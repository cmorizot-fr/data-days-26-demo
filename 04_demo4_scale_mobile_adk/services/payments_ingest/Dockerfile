FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
RUN useradd --uid 10001 --no-create-home app
USER app
# Cloud Run injecte PORT ; 0.0.0.0 est requis dans le conteneur (pas en test local).
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --no-server-header
