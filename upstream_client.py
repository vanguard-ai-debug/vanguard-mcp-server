#!/usr/bin/env python3
"""
Upstream MCP 聚合：将其他 MCP 服务的工具以 ext__服务名__工具名 形式暴露并转发调用。
通过环境变量 MCP_UPSTREAM_CONFIG 配置上游（JSON 数组），例如：
  [{"name": "files", "command": "uvx", "args": ["--from", "mcp", "mcp", "run", "mcp-server-files"]}]
未配置或解析失败时返回空列表，不影响主工具列表。
"""

import json
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 可选：若使用 mcp.types，与主服务一致
try:
    import mcp.types as types
except ImportError:
    types = None

UPSTREAM_PREFIX = "ext__"


def _load_upstream_config() -> List[Dict[str, Any]]:
    raw = os.getenv("MCP_UPSTREAM_CONFIG", "").strip()
    if not raw:
        return []
    try:
        config = json.loads(raw)
        if not isinstance(config, list):
            return []
        return [c for c in config if isinstance(c, dict) and c.get("name") and c.get("command")]
    except json.JSONDecodeError as e:
        logger.warning("MCP_UPSTREAM_CONFIG 解析失败: %s", e)
        return []


def _run_upstream_json_rpc(
    command: List[str],
    method: str,
    params: Dict[str, Any],
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """通过 stdio 向子进程发送 JSON-RPC 请求并返回结果。"""
    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }
    out, err = "", ""
    try:
        out, err = proc.communicate(
            input=json.dumps(request) + "\n",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        return {"error": {"message": "upstream timeout"}}
    if err:
        logger.debug("upstream stderr: %s", err)
    try:
        # 最后一行通常是我们的响应
        for line in reversed((out or "").strip().split("\n")):
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if "result" in data:
                return data["result"]
            if "error" in data:
                return {"error": data["error"]}
    except (json.JSONDecodeError, ValueError):
        pass
    return {"error": {"message": "no valid json-rpc response"}}


def _list_tools_via_stdio(command: List[str], service_name: str) -> List[Any]:
    """对上游 MCP 进程做 initialize + tools/list，返回带前缀的 Tool 列表。
    注意：完整 MCP 需先 initialize 再发 initialized 通知再 tools/list；当前为单次请求，部分上游可能无返回。
    """
    init_result = _run_upstream_json_rpc(
        command,
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "aegis-rag-mcp-upstream", "version": "1.0.0"},
        },
        timeout=10.0,
    )
    if init_result.get("error"):
        logger.warning("upstream %s initialize 失败: %s", service_name, init_result)
        return []
    # 发送 initialized 通知（可选，部分服务需要）
    # 再 list tools
    list_result = _run_upstream_json_rpc(
        command,
        "tools/list",
        {},
        timeout=10.0,
    )
    if list_result.get("error"):
        logger.warning("upstream %s tools/list 失败: %s", service_name, list_result)
        return []
    tools = list_result.get("tools") or []
    out = []
    for t in tools:
        name = t.get("name") or ""
        if not name:
            continue
        prefixed = f"{UPSTREAM_PREFIX}{service_name}__{name}"
        if types is not None:
            out.append(
                types.Tool(
                    name=prefixed,
                    description=(t.get("description") or "").strip() or f"Upstream tool: {name}",
                    inputSchema=t.get("inputSchema") or {"type": "object", "properties": {}},
                )
            )
        else:
            out.append(
                {
                    "name": prefixed,
                    "description": (t.get("description") or "").strip() or f"Upstream tool: {name}",
                    "inputSchema": t.get("inputSchema") or {"type": "object", "properties": {}},
                }
            )
    return out


def fetch_upstream_tools() -> List[Any]:
    """返回所有上游工具的合并列表（名称已加 ext__服务名__ 前缀）。"""
    configs = _load_upstream_config()
    if not configs:
        return []
    all_tools = []
    for c in configs:
        name = c.get("name", "").strip()
        cmd = c.get("command")
        args = c.get("args") or []
        if isinstance(cmd, list):
            command = list(cmd) + list(args)
        else:
            command = [str(cmd)] + [str(a) for a in args]
        if not name or not command:
            continue
        try:
            tools = _list_tools_via_stdio(command, name)
            all_tools.extend(tools)
        except Exception as e:
            logger.warning("获取上游 %s 工具失败: %s", name, e)
    return all_tools


def parse_prefixed_name(prefixed: str) -> Optional[Tuple[str, str]]:
    """解析 ext__服务名__工具名，返回 (service_name, tool_name)。"""
    if not prefixed.startswith(UPSTREAM_PREFIX):
        return None
    rest = prefixed[len(UPSTREAM_PREFIX) :]
    if "__" not in rest:
        return None
    service, tool = rest.split("__", 1)
    return (service.strip(), tool.strip())


def call_upstream_tool(
    service_name: str,
    tool_name: str,
    arguments: Dict[str, Any],
    upstream_config: Optional[List[Dict[str, Any]]] = None,
) -> List[Any]:
    """调用上游工具的 tools/call，返回 MCP 约定的 content 列表（如 TextContent）。"""
    configs = upstream_config or _load_upstream_config()
    for c in configs:
        if (c.get("name") or "").strip() != service_name:
            continue
        cmd = c.get("command")
        args = c.get("args") or []
        if isinstance(cmd, list):
            command = list(cmd) + list(args)
        else:
            command = [str(cmd)] + [str(a) for a in args]
        if not command:
            continue
        result = _run_upstream_json_rpc(
            command,
            "tools/call",
            {"name": tool_name, "arguments": arguments or {}},
            timeout=60.0,
        )
        if result.get("error"):
            err = result["error"]
            msg = err.get("message", str(err))
            if types is not None:
                return [types.TextContent(type="text", text=f"Upstream error: {msg}")]
            return [{"type": "text", "text": f"Upstream error: {msg}"]
        contents = result.get("content") or []
        if types is not None:
            return [
                types.TextContent(type=c.get("type", "text"), text=c.get("text", ""))
                for c in contents
                if isinstance(c, dict)
            ]
        return contents
    if types is not None:
        return [types.TextContent(type="text", text=f"Unknown upstream service: {service_name}")]
    return [{"type": "text", "text": f"Unknown upstream service: {service_name}"}]
