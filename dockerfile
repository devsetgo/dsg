FROM python:3.14-slim-bookworm

WORKDIR /app

LABEL maintainer='Mike Ryan'
LABEL github_repo='https://github.com/devsetgo/dsg'

# Create user before COPY so we can use --chown and avoid a duplicate ownership layer
RUN useradd -m -r dsgUser

# All system deps in one layer: security upgrade + build tools + OCR tools
RUN apt-get update && apt-get -y upgrade \
    && apt-get -y install --no-install-recommends \
        gcc wget gnupg unzip curl \
        tesseract-ocr unpaper ghostscript \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Google Chrome (used for WebLink screenshots)
RUN wget -q -O /usr/share/keyrings/google-chrome.asc https://dl.google.com/linux/linux_signing_key.pub \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.asc] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver pinned to the installed Chrome major version
RUN CHROME_MAJOR=$(google-chrome --version | grep -oP '\d+' | head -1) \
    && CHROMEDRIVER_URL=$(curl -sS "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json" \
        | python3 -c "import sys,json; data=json.load(sys.stdin); versions=[v for v in data['versions'] if v['version'].split('.')[0]=='$CHROME_MAJOR']; url=[d['url'] for d in versions[-1]['downloads'].get('chromedriver',[]) if d['platform']=='linux64'][0]; print(url)") \
    && wget -O /tmp/chromedriver.zip "$CHROMEDRIVER_URL" \
    && unzip /tmp/chromedriver.zip -d /tmp/chromedriver_extracted/ \
    && find /tmp/chromedriver_extracted/ -name "chromedriver" -exec mv {} /usr/local/bin/ \; \
    && rm -rf /tmp/chromedriver.zip /tmp/chromedriver_extracted/

# Copy requirements first for better layer caching — pip layer only rebuilds when requirements change
COPY --chown=dsgUser:dsgUser requirements/ /app/requirements/
RUN pip install --no-cache-dir --upgrade pip setuptools \
    && pip install --no-cache-dir -r requirements/prd.txt

# Copy app with correct ownership in one step — eliminates the duplicate ~319MB chown layer
COPY --chown=dsgUser:dsgUser . /app

USER dsgUser

ENV release_env=prd
ENV DB_DRIVER=sqlite
ENV DB_USERNAME=postgres
ENV DB_PASSWORD=postgres
ENV DB_HOST=postgresdb
ENV DB_PORT=5432
ENV DB_NAME=devsetgo_test
ENV ECHO=False
ENV FUTURE=True
ENV POOL_PRE_PING=False
ENV POOL_RECYCLE=3600
ENV POOL_SIZE=100
ENV MAX_OVERFLOW=100
ENV POOL_TIMEOUT=3600
ENV CREATE_ADMIN_USER=True
ENV ADMIN_USER=<your-github-id>
ENV ADMIN_PASSWORD=<a-password>
ENV ADMIN_EMAIL=<your-email@something.com>
ENV DEFAULT_TIMEZONE=America/New_York
ENV CREATE_DEMO_USER=True
ENV CREATE_DEMO_USERS_QTY=10
ENV CREATE_BASE_CATEGORIES=True
ENV CREATE_DEMO_DATA=True
ENV CREATE_DEMO_NOTES=True
ENV CREATE_DEMO_NOTES_QTY=10
ENV LOGGING_DIRECTORY=log
ENV LOG_NAME=log
ENV LOGGING_LEVEL=DEBUG
ENV LOG_ROTATION="100 MB"
ENV LOG_RETENTION="14 days"
ENV LOG_BACKTRACE=False
ENV LOG_SERIALIZER=False
ENV LOG_DIAGNOSE=False
ENV SAME_SITE=Lax
ENV HTTPS_ONLY=False
ENV MAX_AGE=7200
ENV OPENAI_KEY=<OpenAIKey>
ENV GITHUB_ID=octocat
ENV GITHUB_TOKEN=<githubToken>
ENV GITHUB_REPO_LIMIT=1000
ENV HISTORY_RANGE=3
ENV PORT=5000
ENV WORKERS=1

EXPOSE 5000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "4"]
# CMD ["granian", "--interface", "asgi", "src.main:app", "--host","0.0.0.0", "--port", "5000", "--workers", "4", "--threads", "2", "--http", "1", "--log-level", "debug"]
