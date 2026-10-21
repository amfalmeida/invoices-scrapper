FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY invoices ./invoices
COPY run.py .

RUN useradd --uid 1000 --create-home app && mkdir -p /data && chown app /data
USER app
VOLUME ["/data"]

CMD ["python", "run.py"]
