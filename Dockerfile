# syntax=docker/dockerfile:1
FROM python:3.12-slim AS build

WORKDIR /build
COPY requirements.txt ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt \
    && /opt/venv/bin/pip uninstall -y pip


FROM python:3.12-slim AS runtime

RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    # the runtime image installs nothing at run time; drop pip (and its vendored msgpack/setuptools)
    && python -m pip uninstall -y pip \
    && groupadd --system --gid 10001 vantage \
    && useradd --system --uid 10001 --gid vantage --home-dir /srv/vantage --no-create-home vantage

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/vantage
COPY --from=build /opt/venv /opt/venv
COPY --chown=vantage:vantage app/ ./app/
COPY --chown=vantage:vantage data/seed/ ./data/seed/

USER vantage
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
