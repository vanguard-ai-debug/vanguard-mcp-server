# AegisRAG MCP Server 独立镜像构建
# 构建：docker build -t aegis-mcp-server .
# 运行：docker run -p 8000:8000 -e AEGIS_RAG_BASE_URL=http://<backend>:8080/api/v1 aegis-mcp-server

FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir -e .

ENV AEGIS_RAG_BASE_URL=http://localhost:8080/api/v1
ENV AEGIS_RAG_API_KEY=
EXPOSE 8000

CMD ["aegis-mcp-server"]
