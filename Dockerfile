FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY invoices ./invoices
COPY run.py .

# runs as root: Home Assistant owns /data (options.json) and /share, and a non-root user can't read or write them
RUN mkdir -p /data
VOLUME ["/data"]

CMD ["python", "run.py"]
