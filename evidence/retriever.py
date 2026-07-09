"""
Evidence Retriever — Knowledge Compiler 实现

第一版：遍历 registry 做关键词匹配（v3 plan 确认 Skill.resolve 是 exact match）。
预留 embedding 接口（未来扩展）。

Architecture Decision:
    关键词遍历而非 embedding 检索（v3 plan 确认 Skill 不支持关键词搜索）。
    原因：零依赖（不需要 sentence-transformers），~10 行代码即可工作。
    Phase 0 验证了 Skill("books/acsm12") 在任何 CWD 下均可正确解析路径。
"""

import sys
from typing import Optional

from .base import RetrievalBackend

# KC 以 sys.path fallback 方式加载（pip install -e 因 setuptools 版本 bug 失败）
KC_PATH = r"C:\Users\gbx12\projects\acsms12-manifest"
if KC_PATH not in sys.path:
    sys.path.insert(0, KC_PATH)

from knowledge_compiler import Skill


class KnowledgeCompilerBackend(RetrievalBackend):
    """Knowledge Compiler 检索后端。

    第一版：遍历 registry 做关键词匹配。
    复杂度：O(N) 每查询，N=2305（acsm12 + nsca-cscs）。
    """

    def __init__(self, book_path: str = "books/acsm12"):
        """
        Args:
            book_path: KC book 路径。相对 KC 项目根解析。
                       Phase 0 已确认：Skill 用 __file__ 定位项目根，不依赖 CWD。
        """
        self.skill = Skill(book_path)
        self._registry_items = list(self.skill.registry.items())

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """关键词匹配检索。遍历 registry 做子串匹配。"""
        keywords = query.lower().split()
        matches = []

        for name, oid in self._registry_items:
            # 在规范名称和对象 ID 中搜索关键词
            if any(kw in name.lower() or kw in oid.lower() for kw in keywords):
                try:
                    obj = self.skill.get(name)
                except KeyError:
                    continue

                content = (
                    obj.get("definition")
                    or obj.get("description")
                    or obj.get("signs")
                    or str(obj.get("steps", ""))
                    or ""
                )
                if isinstance(content, list):
                    content = "; ".join(str(c) for c in content)
                content = str(content)[:200]

                matches.append({
                    "id": oid,
                    "type": oid.split(".")[0] if "." in oid else "unknown",
                    "canonical_name": name,
                    "content": content,
                    "source": f"ACSM12 ({name})",
                })

        return matches[:top_k]


class EvidenceRetriever:
    """证据检索器。

    默认使用 Knowledge Compiler 后端。
    可通过替换 backend 切换到其他数据源。
    """

    def __init__(self, backend: Optional[RetrievalBackend] = None):
        self.backend = backend or KnowledgeCompilerBackend()

    def retrieve(self, question: str, top_k: int = 5) -> list[dict]:
        """检索相关证据。"""
        return self.backend.search(question, top_k=top_k)

    def retrieve_with_fallback(self, question: str, top_k: int = 5) -> list[dict]:
        """检索证据 + 空结果降级。永远不会返回 None。"""
        try:
            results = self.retrieve(question, top_k=top_k)
            return results if results else []
        except Exception as exc:
            import warnings
            warnings.warn(f"Retriever failed: {exc}")
            return []
