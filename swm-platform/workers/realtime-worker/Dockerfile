FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends ca-certificates \
	&& rm -rf /var/lib/apt/lists/*

COPY . /app

RUN pip install --no-cache-dir uv \
	&& uv sync --all-packages --frozen --no-dev \
	&& chmod +x /app/scripts/docker/start-worker.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,sys; sys.exit(0 if os.path.exists('/tmp/worker-ready') else 1)"

CMD ["/app/scripts/docker/start-worker.sh", "realtime-worker", "realtime-worker"]
