FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .


RUN pip install --no-cache-dir -r requirements.txt


COPY src/ ./src/


RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

ENV PYTHONPATH=/app/src

# Signal handling for graceful shutdown
STOPSIGNAL SIGTERM

CMD ["python", "src/main.py"]
