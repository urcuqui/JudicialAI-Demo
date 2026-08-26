FROM python:3.11-slim

# Ollama sigue ejecutándose en el host (o en un contenedor aparte), nunca
# dentro de esta imagen: aquí solo vive la aplicación Flask.
WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home /app app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R app:app /app

USER app

ENV PYTHONUNBUFFERED=1 \
    OLLAMA_BASE_URL=http://host.docker.internal:11434 \
    OLLAMA_MODEL=llama3.1:8b

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/case', timeout=3)" || exit 1

# --timeout amplio: las consultas al modelo local pueden tardar más que el
# timeout por defecto de gunicorn (30s), especialmente en modelos grandes.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
