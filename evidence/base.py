"""
Evidence Retrieval — Backend 抽象层

Architecture Decision:
    引入 RetrievalBackend ABC（ChatGPT v2 review 建议），
    而不是直接绑定 Knowledge Compiler Skill API。
    原因：未来可能增加 PubMed / ACSM 官网 / NSCA 等多数据源。
    替换 backend 时 EvidenceRetriever 本身不用改。
"""

from abc import ABC, abstractmethod


class RetrievalBackend(ABC):
    """检索后端抽象接口。"""

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """根据 query 检索相关证据。

        返回格式：
        [
            {
                "id": str,         # 对象 ID
                "type": str,       # 对象类型（Concept / Threshold / ...）
                "canonical_name": str,  # 规范名称
                "content": str,    # 定义/描述（截断至 200 字）
                "source": str,     # 来源（含章节引用）
            },
            ...
        ]
        """
        ...
