FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY migrations ./migrations
RUN pip install --no-cache-dir .
ENV LW_API_DB_PATH=/data/livestock-weight.db
EXPOSE 8000
CMD ["uvicorn", "livestock_weight_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
