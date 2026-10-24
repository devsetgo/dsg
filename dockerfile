FROM python:3.14-slim-bookworm

WORKDIR /app

LABEL maintainer='Mike Ryan'
LABEL github_repo='https://github.com/devsetgo/dsg'

# Create the user before COPY so --chown avoids a duplicate ownership layer.
RUN useradd -m -r dsgUser

# gosu: entrypoint.sh drops from root to dsgUser after fixing volume permissions.
RUN apt-get update && apt-get -y upgrade \
    && apt-get -y install --no-install-recommends gosu \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Requirements first for layer caching - this layer only rebuilds when they change.
COPY --chown=dsgUser:dsgUser requirements/ /app/requirements/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements/prd.txt

COPY --chown=dsgUser:dsgUser . /app

# Both are gitignored, so not in the build context; both are volumes in compose.
RUN mkdir -p /app/log /app/sqlite_db && chown dsgUser:dsgUser /app/log /app/sqlite_db

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV DB_DRIVER=sqlite \
    DB_DIRECTORY=sqlite_db \
    DB_NAME=dsg \
    LOGGING_DIRECTORY=log \
    LOG_NAME=log \
    LOGGING_LEVEL=INFO \
    LOG_ROTATION="100 MB" \
    LOG_RETENTION="14 days" \
    HOST=0.0.0.0 \
    PORT=5000 \
    PROCESSES=8 \
    WORKERS=1

EXPOSE 5000

HEALTHCHECK --interval=1m30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/api/health/status', timeout=5).status == 200 else 1)"

# entrypoint.sh runs as root: fixes volume ownership, migrates, then execs as dsgUser.
ENTRYPOINT ["/entrypoint.sh"]
CMD ["sh", "-c", "exec python -m src.main --processes ${PROCESSES} --workers ${WORKERS} --log-level WARN"]
