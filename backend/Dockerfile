FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# Modelo de embeddings do assistente (busca híbrida): baixado na construção da imagem para a API subir rápido e
# funcionar sem internet. Se o download falhar, a construção continua e a busca usa só BM25 (o /health mostra "assistente_busca": "bm25").
ENV MODELOS_CACHE_DIR=/app/modelos_cache
RUN mkdir -p /app/modelos_cache && python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', cache_dir='/app/modelos_cache')" \
    || echo "AVISO: modelo de embeddings não baixado; a busca usará BM25"

# Usuário sem privilégios de root
RUN useradd --create-home --uid 1000 zela && mkdir -p /app/data && chown -R zela:zela /app
USER zela

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=4s --start-period=40s --retries=8 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

# PORT é definido por plataformas como Render; localmente usa 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
