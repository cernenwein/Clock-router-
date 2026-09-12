FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY clockrouter ./clockrouter
COPY config ./config
RUN pip install --no-cache-dir .

EXPOSE 4000
CMD ["uvicorn", "clockrouter.main:app", "--host", "0.0.0.0", "--port", "4000"]
