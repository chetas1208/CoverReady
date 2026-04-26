FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY apps/api ./apps/api
COPY packages/taxonomy ./packages/taxonomy

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "coverready_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "apps/api"]
