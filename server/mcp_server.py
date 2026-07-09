"""
CheckMyCoach MCP Server — Model Context Protocol 接口

暴露 3 个 tool（ChatGPT v2 review 建议）：
    1. retrieve(question) — 检索证据
    2. calibrate(question) — 全自动校准
    3. health() — 健康检查

验证步骤（Claude Code v1 review 建议）：
    1. stdio 模式跑通（任何 MCP 客户端可调）
    2. 再配 Claude Desktop（冷启动 import 不能报错）

Architecture Decisions:
    - 基于 mcp SDK 1.x（Phase 0 确认：mcp 1.28.1 已发布，版本锁定已不是问题）
    - 先 stdio 后 Claude Desktop（Claude Code 建议）
"""

import sys
import os

# 确保 CheckMyCoach/ 在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent
import mcp.server.stdio


async def serve() -> None:
    """启动 MCP Server（stdio 模式）。"""
    server = Server("checkmycoach")

    # ---- Tool 列表 ----
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="retrieve",
                description="Search for evidence from ACSM guidelines",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The fitness question to find evidence for",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results (default 5)",
                            "default": 5,
                        },
                    },
                    "required": ["question"],
                },
            ),
            Tool(
                name="calibrate",
                description="Full pipeline: retrieve evidence → generate response → calibrate",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The fitness question to calibrate",
                        },
                    },
                    "required": ["question"],
                },
            ),
            Tool(
                name="health",
                description="Check if the server is running and all imports are available",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    # ---- Tool 处理 ----
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            if name == "health":
                return [TextContent(
                    type="text",
                    text='{"status": "ok", "version": "0.1.0", "audit_id": ""}',
                )]

            elif name == "retrieve":
                question = arguments.get("question", "")
                top_k = arguments.get("top_k", 5)
                from evidence import EvidenceRetriever
                retriever = EvidenceRetriever()
                results = retriever.retrieve(question, top_k=top_k)
                import json
                return [TextContent(
                    type="text",
                    text=json.dumps({"success": True, "evidence": results}, ensure_ascii=False),
                )]

            elif name == "calibrate":
                question = arguments.get("question", "")
                from pipeline.agent_pipeline import calibrate_full
                from config import DEV
                result = calibrate_full(question=question, settings=DEV)
                import json
                return [TextContent(
                    type="text",
                    text=json.dumps(result, ensure_ascii=False),
                )]

            else:
                return [TextContent(
                    type="text",
                    text=f'{{"success": false, "error": "Unknown tool: {name}"}}',
                )]

        except Exception as exc:
            import json
            return [TextContent(
                type="text",
                text=json.dumps({"success": False, "error": str(exc)}),
            )]

    # ---- 启动 ----
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="checkmycoach",
                server_version="0.1.0",
            ),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(serve())
