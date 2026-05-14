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
	&& chmod +x /app/scripts/docker/start-api.sh

EXPOSE 8002

HEALTHCHECK --interval=20s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8002/healthz', timeout=3).getcode()==200 else 1)"

CMD ["/app/scripts/docker/start-api.sh", "websocket-api", "websocket-api"]
