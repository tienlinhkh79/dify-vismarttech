FROM dify-notebooklm-retrieval-proxy:local

WORKDIR /app

COPY app /app/app

ENV PORT=8080

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
