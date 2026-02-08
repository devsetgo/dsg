# Use an official Python runtime as a parent image
FROM python:3.13-slim-bookworm

# Set the working directory in the container to /app
WORKDIR /app

# Add metadata to the image
LABEL maintainer='Mike Ryan'
LABEL github_repo='https://github.com/devsetgo/dsg'

# Install gcc, curl, and other dependencies
RUN apt-get update && apt-get -y install gcc wget gnupg unzip curl

# Install Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable

# Install ChromeDriver
RUN CHROME_DRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) \
    && wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/ \
    && rm /tmp/chromedriver.zip

# Install all required dependencies for ocrmypdf functionality
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
	&& apt-get -y install --no-install-recommends \
		tesseract-ocr \
		unpaper \
		ghostscript \
	&& apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip setuptools
RUN pip install --no-cache-dir -r requirements/prd.txt

# Create a user and set file permissions
RUN useradd -m -r dsgUser && chown -R dsgUser /app

# Switch to the new user
USER dsgUser

# Install spaCy and other dependencies
# RUN pip install spacy

# Set environment variables
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
ENV ADMIN_USER=admin
ENV ADMIN_PASSWORD=rules
ENV ADMIN_EMAIL=mikeryan56@gmail.com
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
# Set the port and workers as environment variables
ENV PORT=5000
ENV WORKERS=1
# Make port 5000 available to the world outside this container
EXPOSE 5000

# Run the command to start ASGI server
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "4"]
# CMD ["granian", "--interface", "asgi", "src.main:app", "--host","0.0.0.0", "--port", "5000", "--workers", "4", "--threads", "2", "--http", "1", "--log-level", "debug"]