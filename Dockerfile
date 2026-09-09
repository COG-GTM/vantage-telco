FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

RUN addgroup --system --gid 10001 vantage \
    && adduser --system --uid 10001 --gid 10001 vantage
WORKDIR /srv/vantage
COPY --from=builder /opt/venv /opt/venv
COPY --chown=vantage:vantage app/ /srv/vantage/app/
COPY --chown=vantage:vantage data/seed/ /srv/vantage/data/seed/

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"
USER vantage
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
