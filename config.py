"""
CheckMyCoach — 集中配置管理

Usage:
    from config import DEV, PROD, TEST, Settings

    # 使用默认配置
    cfg = DEV

    # 运行时覆盖
    cfg = Settings(model="deepseek-reasoner", temperature=0.1)

Architecture Decision:
    @dataclass 而非简单常量（ChatGPT v2 review 建议）
    原因：可切 DEV/PROD/TEST 多环境，无需修改代码
    后续可扩展为：从 .env / YAML / 环境变量加载
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    # LLM
    model: str = "deepseek-chat"
    """模型名。已有代码用 deepseek-chat（直连 api.deepseek.com）。
       如果走 OpenRouter，slug 格式为 deepseek/deepseek-chat。
       Phase 0 确认：deepseek-v4-flash 是幻觉命名，不存在。"""

    temperature: float = 0.3
    max_tokens: int = 1024

    # Retriever
    top_k: int = 5
    kc_book_path: str = "books/acsm12"
    """Knowledge Compiler 的 book 路径。相对 KC 项目根解析。"""

    # Pipeline
    api_provider: str = "deepseek"
    """"deepseek" | "openrouter"。决定 API 调用路由。"""

    # Audit
    audit_path: str = "audit/trails.jsonl"
    log_path: str = "audit/runs.log"
    enable_audit: bool = True

    # MCP Server
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000

    # File paths
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.resolve())
    kc_path: str = r"C:\Users\gbx12\projects\acsms12-manifest"
    fitcalib_path: str = r"C:\Users\gbx12\projects\FitCalib-Bench"


# 预设配置
DEV = Settings()
"""开发环境：deepseek-chat, 低 temperature, 审计开"""

PROD = Settings(
    model="deepseek-reasoner",
    temperature=0.1,
    audit_path="audit/prod_trails.jsonl",
)
"""生产环境：更保守的模型, 低随机性, 独立审计文件"""

TEST = Settings(
    audit_path="audit/test_trails.jsonl",
    enable_audit=False,
)
"""测试环境：关审计, 独立日志文件"""
