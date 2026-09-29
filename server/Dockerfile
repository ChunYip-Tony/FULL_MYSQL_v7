FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Build-time validation must not depend on runtime-only App Platform
# secrets/environment variables. Syntax is safe to validate here; import-time
# validation runs from single_service.py after runtime env is available.
RUN python -m compileall -q . \
    && FULLMYSQL_WORK_TOKEN=build-smoke python -c "import api; print(api.VERSION)"
CMD ["python","single_service.py"]
