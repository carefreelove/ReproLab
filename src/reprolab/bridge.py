"""Synchronous mini-swe-agent environment backed by a persistent stdio MCP client."""

import functools
import json
import sys

from anyio.from_thread import start_blocking_portal
from mcp import Client, StdioServerParameters

from reprolab.core import LabError, redact
from reprolab.store import Store


class MCPEnvironment:
    def __init__(self, store: Store, run_id: str):
        self.store, self.run_id = store, run_id
        self.config = {"transport": "stdio", "server": "reprolab.mcp_server"}
        self.portal_manager = start_blocking_portal()
        self.portal = self.portal_manager.__enter__()
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "reprolab.mcp_server", "--run-id", run_id, "--home", str(store.home)],
            env={"REPROLAB_HOME": str(store.home), "MSWEA_SILENT_STARTUP": "1"},
        )
        self.client_manager = self.portal.wrap_async_context_manager(Client(parameters))
        try:
            self.client = self.client_manager.__enter__()
            listed = self.portal.call(self.client.list_tools)
            self.tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema,
                    },
                }
                for tool in listed.tools
            ]
            self.store.event(
                run_id,
                "mcp_connected",
                {
                    "protocol": self.client.protocol_version,
                    "transport": "stdio",
                    "tools": [tool["function"]["name"] for tool in self.tools],
                },
            )
            self.store.put(run_id, "runtime", "tool_schemas", self.tools)
        except BaseException:
            self.portal_manager.__exit__(*sys.exc_info())
            raise

    def execute(self, action: dict, cwd: str = "") -> dict:
        if self.store.get(self.run_id, "runtime", "stop"):
            raise LabError("no_progress", "相同动作与结果连续出现三次，已保存调查缺口")
        self.store.put(self.run_id, "runtime", "operation", action["id"])
        try:
            result = self.portal.call(
                functools.partial(
                    self.client.call_tool,
                    action["name"],
                    action["arguments"],
                    90.0,
                    meta={"reprolab/operation": action["id"]},
                )
            )
        except Exception as exc:
            code = "mcp_timeout" if isinstance(exc, TimeoutError) else "mcp_transport"
            self.store.event(self.run_id, "mcp_transport_error", {"code": code, "type": type(exc).__name__})
            raise LabError(code, "MCP 调用中断，已保存状态，可通过 resume 重试") from exc
        if result.is_error:
            detail = " ".join(block.text for block in result.content if hasattr(block, "text"))
            self.store.event(
                self.run_id,
                "mcp_tool_error",
                {"tool": action["name"], "operation_id": action["id"], "detail": redact(detail)[:1200]},
            )
            return {"ok": False, "error": {"code": "mcp_tool", "message": redact(detail)[:1200]}}
        if result.structured_content is not None:
            return result.structured_content
        text = "".join(block.text for block in result.content if hasattr(block, "text"))
        try:
            return json.loads(text)
        except ValueError as exc:
            raise LabError("mcp_format", "MCP 工具返回无法解析的结果") from exc

    def get_template_vars(self, **kwargs):
        return {}

    def serialize(self):
        return {
            "info": {
                "config": {"environment": self.config, "environment_type": "reprolab.bridge.MCPEnvironment"}
            }
        }

    def close(self):
        try:
            self.client_manager.__exit__(None, None, None)
        finally:
            self.portal_manager.__exit__(None, None, None)
