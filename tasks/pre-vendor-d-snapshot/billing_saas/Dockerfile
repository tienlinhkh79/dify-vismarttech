FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir "fastapi>=0.115.0" "python-multipart>=0.0.9" "uvicorn[standard]>=0.32.0"

COPY plan_catalog.json /app/plan_catalog.json
COPY app /app/app

ENV BILLING_PLAN_CATALOG_PATH=/app/plan_catalog.json
ENV BILLING_SAAS_DB_PATH=/data/billing_saas.db
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
