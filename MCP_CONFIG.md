# 使用 uv 运行 AegisRAG MCP 服务器

> 更推荐使用`uv`来运行基于python的MCP服务。

## 1. 安装 uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 Homebrew (macOS)
brew install uv

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 2. MCP 客户端配置

### Claude Desktop 配置

在 Claude Desktop 设置中添加:

```json
{
  "mcpServers": {
    "aegis-rag": {
      "args": [
        "--directory",
        "/path/AegisRAG/mcp-server",
        "run",
        "run_server.py"
      ],
      "command": "uv",
      "env": {
        "AEGIS_RAG_API_KEY": "your_api_key_here",
        "AEGIS_RAG_BASE_URL": "http://localhost:8080/api/v1"
      }
    }
  }
}
```

### Cursor 配置

在 Cursor 中，编辑 MCP 配置文件 (通常在 `~/.cursor/mcp-config.json`):

```json
{
  "mcpServers": {
    "aegis-rag": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/AegisRAG/mcp-server",
        "run",
        "run_server.py"
      ],
      "env": {
        "AEGIS_RAG_API_KEY": "your_api_key_here",
        "AEGIS_RAG_BASE_URL": "http://localhost:8080/api/v1"
      }
    }
  }
}
```

### KiloCode 配置

对于 KiloCode 或其他支持 MCP 的编辑器，配置如下:

```json
{
  "mcpServers": {
    "aegis-rag": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/AegisRAG/mcp-server",
        "run",
        "run_server.py"
      ],
      "env": {
        "AEGIS_RAG_API_KEY": "your_api_key_here",
        "AEGIS_RAG_BASE_URL": "http://localhost:8080/api/v1"
      }
    }
  }
}
```

### 其他 MCP 客户端

对于一般 MCP 客户端配置:

```json
{
  "mcpServers": {
    "aegis-rag": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/AegisRAG/mcp-server",
        "run",
        "run_server.py"
      ],
      "env": {
        "AEGIS_RAG_API_KEY": "your_api_key_here",
        "AEGIS_RAG_BASE_URL": "http://localhost:8080/api/v1"
      }
    }
  }
}
```

## 3. 上游 MCP 工具聚合（可选）

本服务可将其他 MCP 服务的工具以 `ext__服务名__工具名` 形式一并暴露，调用时自动转发到对应上游。

设置环境变量 `MCP_UPSTREAM_CONFIG` 为 JSON 数组，每项包含：`name`（服务名）、`command`（可执行命令）、`args`（可选参数）。不配置或留空时仅暴露 AegisRAG 原生工具。
