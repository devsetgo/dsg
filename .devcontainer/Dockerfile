FROM mcr.microsoft.com/devcontainers/python:1-3.12

ENV PYTHONUNBUFFERED 1

# Install Docker CLI
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends docker.io \
    && rm -rf /var/lib/apt/lists/*

# Use the Docker group ID from the host machine
ARG DOCKER_GID=1001

# Check if the docker group exists before creating it
RUN if ! getent group docker > /dev/null 2>&1; then groupadd -g ${DOCKER_GID} docker; fi && \
    usermod -aG docker vscode

# Ensure the Docker socket has the correct permissions if it exists
RUN if [ -S /var/run/docker.sock ]; then chmod 666 /var/run/docker.sock; fi

# [Optional] If your requirements rarely change, uncomment this section to add them to the image.
# COPY requirements.txt /tmp/pip-tmp/
# RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
#    && rm -rf /tmp/pip-tmp

# [Optional] Uncomment this section to install additional OS packages.
# RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
#     && apt-get -y install --no-install-recommends <your-package-list-here>