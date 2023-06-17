#!/bin/bash
set -e
set -x


IMAGE_NAME="dsg"
IMAGE_VERSION=$(TZ=America/New_York date +"%y-%m-%d")
echo 'Docker Build Python'
docker build -t mikeryan56/$IMAGE_NAME:$IMAGE_VERSION-rc .
# docker build -t mikeryan56/$IMAGE_NAME:$IMAGE_VERSION -t mikeryan56/$IMAGE_NAME:latest -f ./dockerfiles/dockerfile_python .
# echo "Running Docker Image"
# docker run mikeryan56/test-api:$CAL_VER-python38
echo "Push"
docker push mikeryan56/$IMAGE_NAME:$IMAGE_VERSION-rc
# docker push mikeryan56/$IMAGE_NAME:latest
# echo 'Docker Build with PyPy'
# docker build -t mikeryan56/test-api:$CAL_VER -f ./docker/dockerfile_pypy .