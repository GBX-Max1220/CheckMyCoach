"""
Agent Pipeline — CheckMyCoach 校准管线

两条路径：
    calibrate(response, question)       — 校准已有回答（灵活）
    calibrate_full(question)            — 全自动：KC → LLM → UCS → M1-M4（demo 友好）

Architecture Decisions:
    - 返回 dict（TypedDict schema）而非 dataclass（ChatGPT v1 建议）。便于迭代加字段。
    - calibrate_full 是 calibrate 的 wrapper（Claude Code 建议）。代码量差不到 10 行。
    - 每条路径都有 try-except 降级（Coze v1 建议）。不会因为单步异常整条管线断掉。
    - score_delta 注释说明测量噪声（Claude Code v2 确认 + v3 plan 落实）。
"""

import json
import time
import uuid
import warnings
from datetime import datetime, timezone
from typing import Optional

from config import DEV, Settings
from schema import CalibrateResult


# ============================================================
# 延迟导入（Phase 0 确认所有依赖可用）
# ============================================================

def _import_ucs_engine():
    """Lazy import: UCS engine from FitCalib-Bench (external dependency, not frozen)."""
    import sys
    _ensure_repo_root_on_path()
    sys.path.insert(0, r"C:\Users\gbx12\projects\FitCalib-Bench")
    from evaluation.ucs_engine import evaluate_ucs
    return evaluate_ucs


def _ensure_repo_root_on_path():
    """Ensure CheckMyCoach repo root is on sys.path for frozen local imports."""
    import sys
    from pathlib import Path
    root = str(Path(__file__).resolve().parent.parent)
    if root not in sys.path:
        sys.path.insert(0, root)


def _import_m1():
    _ensure_repo_root_on_path()
    from calibration_agent.m1_detection import needs_calibration
    return needs_calibration


def _import_m2():
    _ensure_repo_root_on_path()
    from calibration_agent.m2_diagnosis import diagnose
    return diagnose


def _import_m3():
    _ensure_repo_root_on_path()
    from calibration_agent.m3_correction import correct
    return correct


def _import_m4():
    _ensure_repo_root_on_path()
    from calibration_agent.m4_validation import validate
    return validate


def _import_retriever():
    from evidence.retriever import EvidenceRetriever
    return EvidenceRetriever


def _import_llm_client(settings=None):
    """DeepSeek Chat API 客户端。"""
    import os
    import requests
    from dotenv import load_dotenv

    load_dotenv()
    cfg = settings or Settings()

    def call_llm(prompt: str, model: str = "deepseek-chat",
                 temperature: float = 0.3, max_tokens: int = 1024) -> dict:
        provider = (cfg.api_provider if hasattr(cfg, 'api_provider') else 'deepseek')
        if provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            url = "https://openrouter.ai/api/v1/chat/completions"
        else:
            api_key = os.getenv("DEEPSEEK_API_KEY")
            url = "https://api.deepseek.com/chat/completions"

        if not api_key:
            raise ValueError(f"No API key found for provider: {provider}")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        usage = data.get("usage", {})
        token_info = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        }
        # DeepSeek 价格：约 $0.014/M input tokens, $0.028/M output tokens
        prompt_cost = token_info["prompt_tokens"] * 0.000014
        completion_cost = token_info["completion_tokens"] * 0.000028
        token_info["cost"] = round(prompt_cost + completion_cost, 6)

        return {
            "text": data["choices"][0]["message"]["content"],
            "token_usage": token_info,
        }

    return call_llm


# ============================================================
# 核心函数
# ============================================================

def calibrate(
    response: str,
    question: str,
    evidence: Optional[list[dict]] = None,
    history: Optional[list[dict]] = None,
    metadata: Optional[dict] = None,
    settings: Optional[Settings] = None,
) -> CalibrateResult:
    """路径 A：校准已有回答。

    Args:
        response: LLM 生成的原始回答
        question: 用户提问
        evidence: 预检索的证据。None 则管线内自动检索。
        history: 对话历史（预留，当前未实现）
        metadata: 额外元数据（预留，当前未实现）
        settings: 配置覆盖。None 则使用 DEV。

    Returns:
        CalibrateResult (TypedDict)，含统一错误格式 {success, result, error, audit_id}
    """
    cfg = settings or DEV
    audit_id = _generate_audit_id()
    result: CalibrateResult = {
        "success": True,
        "audit_id": audit_id,
        "question": question,
        "path": "calibrate",
        "ucs_score": -1,
        "needs_calibration": False,
        "m4_passed": True,
        "error": None,
    }
    timings = {}

    try:
        # ---- Step 0: 检索证据 ----
        t0 = time.perf_counter()
        if evidence is None:
            try:
                retriever_cls = _import_retriever()
                retriever = retriever_cls()
                evidence = retriever.retrieve_with_fallback(question, top_k=cfg.top_k)
            except Exception as exc:
                warnings.warn(f"Retriever failed, continuing without evidence: {exc}")
                evidence = []
        result["evidence"] = evidence
        timings["retriever"] = (time.perf_counter() - t0) * 1000

        # ---- Step 1: UCS Engine ----
        t1 = time.perf_counter()
        evaluate_ucs = _import_ucs_engine()
        ucs_result = evaluate_ucs(response=response, question=question)
        result["ucs_score"] = int(ucs_result.ucs_score)
        if ucs_result.extraction:
            result["extraction_features"] = {
                "claims_superiority": ucs_result.extraction.claims_superiority,
                "has_directional_claim": ucs_result.extraction.has_directional_claim,
                "mentions_no_difference": ucs_result.extraction.mentions_no_difference,
                "has_hedging": ucs_result.extraction.has_hedging,
                "cites_evidence_type": ucs_result.extraction.cites_evidence_type,
            }
        timings["ucs_engine"] = (time.perf_counter() - t1) * 1000

        # ---- Step 2: M1 Detection ----
        t2 = time.perf_counter()
        needs_calibration = _import_m1()
        should_calibrate, reason = needs_calibration(
            ucs_score=result["ucs_score"],
            needs_manual_review=ucs_result.needs_manual_review,
            review_reason=ucs_result.review_reason,
        )
        result["needs_calibration"] = should_calibrate
        timings["m1"] = (time.perf_counter() - t2) * 1000

        if not should_calibrate:
            result["response"] = response
            result["failure_type"] = None
            result["corrected_response"] = None
            result["score_delta"] = 0.0
            timings.setdefault("total", sum(v for v in timings.values() if isinstance(v, (int, float))))
            result["latency_ms"] = timings
            _write_audit(result, cfg)
            return result

        # ---- Step 3: M2 Diagnosis ----
        t3 = time.perf_counter()
        diagnose = _import_m2()
        feats = result.get("extraction_features", {})
        diag = diagnose(
            ucs_score=result["ucs_score"],
            claims_superiority=feats.get("claims_superiority", False),
            has_directional_claim=feats.get("has_directional_claim", False),
            mentions_no_difference=feats.get("mentions_no_difference", False),
            has_hedging=feats.get("has_hedging", False),
        )
        result["failure_type"] = diag.failure_type.value if hasattr(diag.failure_type, "value") else str(diag.failure_type)
        result["m2_confidence"] = diag.confidence
        timings["m2"] = (time.perf_counter() - t3) * 1000

        # ---- Step 4: M3 Correction ----
        t4 = time.perf_counter()
        correct = _import_m3()
        try:
            # Format evidence text from the evidence list
            evidence_text = ""
            ev_list = result.get("evidence") or []
            if ev_list:
                excerpts = [e.get("content", "") for e in ev_list if e.get("content")]
                evidence_text = "\n".join(excerpts[:3])
            correction = correct(
                diag.failure_type, response,
                question=question,
                evidence=evidence_text,
            )
            corrected_text = correction.corrected_text
            result["m3_source"] = correction.source
        except Exception as exc:
            warnings.warn(f"M3 correction failed, using fallback: {exc}")
            corrected_text = response
            result["m3_source"] = "fallback"
        timings["m3"] = (time.perf_counter() - t4) * 1000

        # ---- Step 5: M4 Validation ----
        t5 = time.perf_counter()
        validate = _import_m4()
        try:
            vr = validate(corrected_text, response)
            result["corrected_response"] = vr.final_text
            result["m4_passed"] = (vr.final_text != response)
        except Exception as exc:
            warnings.warn(f"M4 validation failed, falling back to original: {exc}")
            result["corrected_response"] = response
            result["m4_passed"] = False
        timings["m4"] = (time.perf_counter() - t5) * 1000

        # ---- Step 6: Score Delta (approx) ----
        # ⚠️ UCS 有测量噪声（LLM 分支非确定性），不作为论文定量指标
        t6 = time.perf_counter()
        try:
            ucs_after = evaluate_ucs(
                response=result.get("corrected_response", response),
                question=question,
            )
            result["score_delta"] = float(ucs_after.ucs_score - result["ucs_score"])
        except Exception:
            result["score_delta"] = None
        timings["score_delta"] = (time.perf_counter() - t6) * 1000

        # ---- Final ----
        result["response"] = response
        result["latency_ms"] = timings
        timings.setdefault("total", sum(v for v in timings.values()))

        _write_audit(result, cfg)
        return result

    except Exception as exc:
        # 顶层异常兜底：确保总是返回统一格式
        result["success"] = False
        result["error"] = f"PIPELINE_ERROR: {exc}"
        result["latency_ms"] = timings
        return result


def calibrate_full(
    question: str,
    context: Optional[list[dict]] = None,
    history: Optional[list[dict]] = None,
    metadata: Optional[dict] = None,
    settings: Optional[Settings] = None,
) -> CalibrateResult:
    """路径 B：全自动校准（demo 友好）。

    calibrate() 的 wrapper，多一步：
    0. KC 检索证据 → LLM(deepseek-chat) → 生成回答 → 然后走 calibrate()
    """
    cfg = settings or DEV
    audit_id = _generate_audit_id()
    result: CalibrateResult = {
        "success": True,
        "audit_id": audit_id,
        "question": question,
        "path": "calibrate_full",
        "ucs_score": -1,
        "needs_calibration": False,
        "m4_passed": True,
        "error": None,
    }
    timings = {}

    try:
        # Step 0a: 检索证据
        t0 = time.perf_counter()
        if context:
            evidence = context
        else:
            try:
                retriever_cls = _import_retriever()
                retriever = retriever_cls()
                evidence = retriever.retrieve_with_fallback(question, top_k=cfg.top_k)
            except Exception as exc:
                warnings.warn(f"Retriever failed: {exc}")
                evidence = []
        result["evidence"] = evidence
        timings["retriever"] = (time.perf_counter() - t0) * 1000

        # Step 0b: LLM 生成回答
        t_llm = time.perf_counter()
        try:
            llm_client = _import_llm_client(settings=cfg)
            evidence_text = "\n".join(
                f"[{e.get('source', '?')}] {e.get('content', '')}"
                for e in evidence
            ) if evidence else "No specific evidence found."

            prompt = (
                f"You are a fitness expert. Answer the following question "
                f"based on ACSM guidelines.\n\n"
                f"Evidence:\n{evidence_text}\n\n"
                f"Question: {question}\n\n"
                f"Provide a concise, evidence-based answer."
            )

            llm_result = llm_client(
                prompt=prompt,
                model=cfg.model,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
            )
            response_text = llm_result["text"]
            result["token_usage"] = llm_result.get("token_usage", {})
        except Exception as exc:
            result["success"] = False
            result["error"] = f"LLM_ERROR: {exc}"
            result["latency_ms"] = timings
            return result
        timings["llm"] = (time.perf_counter() - t_llm) * 1000

        # Step 1-6: 走 calibrate
        cal_result = calibrate(
            response=response_text,
            question=question,
            evidence=evidence,
            settings=cfg,
        )
        cal_result["audit_id"] = audit_id
        # Merge timings: calibrate_full (retriever+llm) + calibrate (ucs+m1-m4)
        cal_timings = cal_result.get("latency_ms", {}) or {}
        merged_timings = {**cal_timings, **timings}
        cal_result["latency_ms"] = merged_timings
        if cal_result.get("token_usage"):
            cal_result["token_usage"] = result.get("token_usage", {})

        return cal_result

    except Exception as exc:
        result["success"] = False
        result["error"] = f"PIPELINE_ERROR: {exc}"
        return result


# ============================================================
# 内部工具
# ============================================================

def _generate_audit_id() -> str:
    now = datetime.now(timezone.utc)
    short_id = uuid.uuid4().hex[:8]
    return f"cmc_{now.strftime('%Y%m%d_%H%M%S')}_{short_id}"


def _write_audit(result: CalibrateResult, settings: Settings) -> None:
    """写入 audit JSONL。写入失败不阻塞主流程。"""
    if not settings.enable_audit:
        return
    try:
        import json, os
        path = settings.audit_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        record = {
            "audit_id": result.get("audit_id"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": result.get("path"),
            "question": result.get("question"),
            "evidence_ids": [e.get("id") for e in result.get("evidence", [])],
            "response": result.get("response"),
            "ucs_score": result.get("ucs_score"),
            "extraction_features": result.get("extraction_features"),
            "m1_decision": "calibrate" if result.get("needs_calibration") else "pass",
            "m2_failure_type": result.get("failure_type"),
            "m2_confidence": result.get("m2_confidence"),
            "m3_corrected": result.get("corrected_response"),
            "m4_passed": result.get("m4_passed"),
            "score_delta": result.get("score_delta"),
            "latency_ms": result.get("latency_ms"),
            "token_usage": result.get("token_usage"),
            "pre_trust_score": None,
            "decision_change": None,
            "user_profile": None,
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        warnings.warn(f"Audit write failed (non-blocking): {exc}")
