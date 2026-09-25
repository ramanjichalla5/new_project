FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    MOCK_LLM=1 HF_HOME=/opt/huggingface CHROMA_PATH=/app/runtime/chroma \
    ANONYMIZED_TELEMETRY=False TOKENIZERS_PARALLELISM=false
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt
# Fetch the public model at image build time; requests at runtime need no network.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2').save('/opt/minilm')"
ENV EMBEDDING_MODEL=/opt/minilm HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
COPY support_assistant /app/support_assistant
RUN useradd --create-home --uid 10001 appuser && mkdir -p /app/runtime && chown -R appuser:appuser /app /opt/minilm
USER appuser
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/health', timeout=4)"
CMD ["uvicorn", "support_assistant.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
