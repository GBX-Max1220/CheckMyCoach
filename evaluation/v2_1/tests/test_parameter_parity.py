"""
test_parameter_parity.py — Verify all correction conditions have identical generation parameters.

Fix 2 requirement:
- All three correction conditions: temperature=0.3, max_tokens=1024
- No env var overrides for model selection
"""

import inspect
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evaluation.v2_1.runner.run_single_case import MODEL_CONFIG, ALL_CONDITIONS
from calibration_agent.m3_correction import _call_llm as m3_call_llm
from evaluation.v2_1.runner.generic_correction import correct as generic_correct

PASS = 0
FAIL = 0
ERRORS = []

def run_test(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  PASS  {name}")
    except AssertionError as e:
        FAIL += 1
        msg = str(e) if str(e) else "assertion failed"
        print(f"  FAIL  {name}: {msg}")
        ERRORS.append(f"{name}: {msg}")
    except Exception as e:
        FAIL += 1
        print(f"  FAIL  {name}: {type(e).__name__}: {e}")
        ERRORS.append(f"{name}: {type(e).__name__}: {e}")


# ── MODEL_CONFIG parity ──

def test_all_correction_conditions_temperature_0_3():
    """All three LLM conditions have temperature=0.3 in MODEL_CONFIG."""
    for cond in ["generic", "generic_with_diagnosis", "checkmycoach_m3"]:
        cfg = MODEL_CONFIG[cond]
        assert cfg["temperature"] == 0.3, \
            f"{cond} temperature={cfg['temperature']}, expected 0.3"


def test_all_correction_conditions_max_tokens_1024():
    """All three LLM conditions have max_tokens=1024 in MODEL_CONFIG."""
    for cond in ["generic", "generic_with_diagnosis", "checkmycoach_m3"]:
        cfg = MODEL_CONFIG[cond]
        assert cfg["max_tokens"] == 1024, \
            f"{cond} max_tokens={cfg['max_tokens']}, expected 1024"


def test_all_correction_conditions_same_model():
    """All three LLM conditions use openai/gpt-4o-mini."""
    for cond in ["generic", "generic_with_diagnosis", "checkmycoach_m3"]:
        cfg = MODEL_CONFIG[cond]
        assert cfg["model_id"] == "openai/gpt-4o-mini", \
            f"{cond} model={cfg['model_id']}, expected openai/gpt-4o-mini"


def test_all_correction_conditions_same_provider():
    """All three LLM conditions use openrouter."""
    for cond in ["generic", "generic_with_diagnosis", "checkmycoach_m3"]:
        cfg = MODEL_CONFIG[cond]
        assert cfg["provider"] == "openrouter", \
            f"{cond} provider={cfg['provider']}, expected openrouter"


# ── No env var overrides ──

def test_generic_correction_hardcodes_model():
    """generic_correction.py does not use os.getenv for model."""
    src = inspect.getsource(generic_correct)
    # Should NOT have os.getenv for the model
    assert 'os.getenv("GENERIC_MODEL"' not in src, \
        "Generic correction should hardcode model, not use env var"
    # Should hardcode the model name
    assert '"openai/gpt-4o-mini"' in src, \
        "Generic correction should hardcode openai/gpt-4o-mini"


def test_m3_correction_hardcodes_model():
    """m3_correction.py _call_llm does not use os.getenv for model."""
    src = inspect.getsource(m3_call_llm)
    assert 'os.getenv("M3_MODEL"' not in src, \
        "M3 correction should hardcode model, not use env var"
    assert '"openai/gpt-4o-mini"' in src, \
        "M3 correction should hardcode openai/gpt-4o-mini"


def test_m3_correction_hardcodes_temperature():
    """m3_correction.py _call_llm hardcodes temperature=0.3."""
    src = inspect.getsource(m3_call_llm)
    assert "temperature=0.3" in src, \
        "M3 correction should hardcode temperature=0.3"


def test_m3_correction_hardcodes_max_tokens():
    """m3_correction.py _call_llm hardcodes max_tokens=1024."""
    src = inspect.getsource(m3_call_llm)
    assert "max_tokens=1024" in src, \
        "M3 correction should hardcode max_tokens=1024"


# ── model_config.json parity ──

def test_model_config_matches_MODEL_CONFIG():
    """model_config.json values match run_single_case.py MODEL_CONFIG."""
    import json
    config_path = REPO_ROOT / "evaluation" / "v2_1" / "runner" / "model_config.json"
    config = json.loads(config_path.read_text())

    # Generic
    assert config["generic_correction"]["temperature"] == MODEL_CONFIG["generic"]["temperature"]
    assert config["generic_correction"]["max_tokens"] == MODEL_CONFIG["generic"]["max_tokens"]

    # Generic+Diagnosis
    assert config["generic_plus_correction"]["temperature"] == MODEL_CONFIG["generic_with_diagnosis"]["temperature"]
    assert config["generic_plus_correction"]["max_tokens"] == MODEL_CONFIG["generic_with_diagnosis"]["max_tokens"]

    # CMC M3
    assert config["cmc_m3_correction"]["temperature"] == MODEL_CONFIG["checkmycoach_m3"]["temperature"]
    assert config["cmc_m3_correction"]["max_tokens"] == MODEL_CONFIG["checkmycoach_m3"]["max_tokens"]

    # All equal
    temps = [config[k]["temperature"] for k in ["generic_correction", "generic_plus_correction", "cmc_m3_correction"]]
    tokens = [config[k]["max_tokens"] for k in ["generic_correction", "generic_plus_correction", "cmc_m3_correction"]]
    assert len(set(temps)) == 1, f"Not all temperatures equal: {temps}"
    assert len(set(tokens)) == 1, f"Not all max_tokens equal: {tokens}"


if __name__ == "__main__":
    print("=" * 60)
    print("Parameter Parity Tests — Fix 2")
    print("=" * 60)
    tests = [t for t in dir() if t.startswith("test_")]
    for t in tests:
        run_test(t, globals()[t])
    print("=" * 60)
    print(f"Results: {PASS}/{PASS + FAIL} passed ({FAIL} failed)")
    if ERRORS:
        for e in ERRORS:
            print(f"  FAIL  {e}")
    raise SystemExit(0 if FAIL == 0 else 1)
