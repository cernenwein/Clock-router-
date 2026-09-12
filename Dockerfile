FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY clockrouter ./clockrouter
COPY config ./config
RUN pip install --no-cache-dir .

RUN addgroup --system clockrouter && adduser --system --ingroup clockrouter clockrouter
USER clockrouter

EXPOSE 4000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4000/health', timeout=2)"]
CMD ["uvicorn", "clockrouter.main:app", "--host", "0.0.0.0", "--port", "4000"]
