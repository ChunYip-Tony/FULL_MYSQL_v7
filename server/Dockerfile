FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Catch Python syntax/import-time failures during image build instead of
# discovering them only after App Platform starts the container.
RUN python -m compileall -q . \
    && python -c "import api; import worker; print('FULL MYSQL startup import smoke PASS')"
CMD ["python","single_service.py"]
