FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN uv pip install --system notebooklm-mcp-cli

ENV NOTEBOOKLM_TRANSPORT=http \
    NOTEBOOKLM_PORT=8010 \
    NOTEBOOKLM_HOST=0.0.0.0 \
    NOTEBOOKLM_ALLOW_EXTERNAL_BIND=1

EXPOSE 8010

CMD ["notebooklm-mcp", "--transport", "http", "--port", "8010", "--host", "0.0.0.0"]
