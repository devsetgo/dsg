---
title: "Starlette Dashboard"
date: 2019-11-30T12:00:00-00:00
description: "A Dshboard template for Starlette"
draft: false
featured_image: "../images/starlette.png"

---
{{< figure src="/images/starlette.png" width="800" alt="Starlette" >}}


This project is to serve as an experiment to learn [starlette](https://starlette.io/) and a basic template for other projects. It is built with the [AdminLTE V3.0.1](https://adminlte.io/) HTML template

Currently running at [stardash.devsetgo.com/](https://stardash.devsetgo.com/)
{{< figure src="/images/image_1.png" width="800" alt="Starlette Dashboard" >}}

Would love to have [help to build a great example](https://github.com/devsetgo/starlette-dashboard) for others to use or just [fork it](https://github.com/devsetgo/starlette-dashboard) for your own use.

Python:

![image](https://img.shields.io/badge/calver-YYYY.MM.DD-22bfda.svg "CalVer")
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg">
[![Python 3.6](https://img.shields.io/badge/python-3.6-blue.svg)](https://www.python.org/downloads/release/python-360/)
[![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/)

CI/CD Pipeline:

[![codecov](https://codecov.io/gh/devsetgo/starlette-dashboard/branch/master/graph/badge.svg)](https://codecov.io/gh/devsetgo/starlette-dashboard)
[![Actions Status](https://github.com/devsetgo/starlette-dashboard/workflows/Run%20Tests/badge.svg)](https://github.com/devsetgo/starlette-dashboard/actions)
[![Actions Status](https://github.com/devsetgo/starlette-dashboard/workflows/Docker%20Latest/badge.svg)](https://github.com/devsetgo/starlette-dashboard/actions)

SonarCloud:

[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=devsetgo_starlette-dashboard&metric=sqale_rating)](https://sonarcloud.io/dashboard?id=devsetgo_starlette-dashboard)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=devsetgo_starlette-dashboard&metric=reliability_rating)](https://sonarcloud.io/dashboard?id=devsetgo_starlette-dashboard)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=devsetgo_starlette-dashboard&metric=alert_status)](https://sonarcloud.io/dashboard?id=devsetgo_starlette-dashboard)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=devsetgo_starlette-dashboard&metric=bugs)](https://sonarcloud.io/dashboard?id=devsetgo_starlette-dashboard)

<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>

# Starlette - Dashboard Template

Note: The template has thousands of issues according to SonarCloud. All are due to template issues and issues within JavaScript for UI dependencies. Working on determining a way to solve these issues.

Utilizing Starlette to render the [AdminLTE](https://adminlte.io/) template. This is a basic example to be used as the base/skeleton/template for Starlette applciations.

![Starlette Dashboard](https://raw.githubusercontent.com/devsetgo/starlette-dashboard/release-candidate/screenshots/image_1.png)

### Use it
- git clone https://github.com/devsetgo/starlette-dashboard
- create a virtualenv on linux or Windows Subsystem Linux

#### Run APP
First Change directory to app

UVICORN
    Development:
~~~~
    uvicorn main:app --port 5000 --reload
    python3 main.py
~~~~
    Production:
~~~~
    uvicorn main:app --workers 2 --port 5000
    gunicorn -c gunicorn_cfg.py main:app
    # Note: gunicorn is the config for the dockerfile
~~~~

Docker
~~~~
    Docker: docker pull mikeryan56/starlette-dashboard:latest (not implemented)
~~~~

#### Run Tests
~~~~
python3 -m pytest
~~~~

#### Create coverage badge
~~~~
    coverage-badge -o coverage.svg -f
~~~~

#### Pre-Commit & Hooks
~~~~
    - Follow install instructionsL: [https://pre-commit.com/#install](https://pre-commit.com/#install)
    - pre-commit install
    - pre-commit run -a
~~~~

## Issues/Bugs

- [ ] cleanup

## TODO

- [x] Create tests
    - [x] Minimum of 80%
    - [x] Exception Testing
    - [ ] Mock [requests](https://2.python-requests.org/en/master/) call
- [x] Better organization
    - [x] Use of Endpoints (equivalent to Flask Blueprints) - starlette routes and endpoint (/app/routes)
- [x] Configuration Scripts

- [ ] Access Controls
  - [ ] Add Access controls
  - [ ] Signup functionality

- [x] Gunicorn/Uvicorn configuration
- [x] Logging (using [Loguru](https://github.com/Delgan/loguru))
- [x] Setup CI/CD Pipeline for test and deployment
    - [x] [SonarCloud](https://sonarcloud.io)
    - [x] [Github Actions](https://github.com/features/actions) found in .github/workflow/actions
        - [x] tests - matrix run of Python 3.6 and 3.7
            - [x] CodeCove.io upload
        - [x] docker-rc - docker build and push when pull request approved for release-candidate branch (calendar version - rc)
        - [x] docker-master - docker build and push when pull request approved for master branch (calender version and latest)
        - [x] ensure docker build only happens after pull_request approved and merged into higher branch
- [x] [Twelve Factor App](https://12factor.net/) ready
- [ ] Build a [cookiecutter](https://github.com/audreyr/cookiecutter) template for
- [x] Add code comments
- [ ] Websocket example

- Docker
  - [x] Docker Image
  - [x] Docker-Compose
    - [ ] Docker Swarm settings
  - [ ] Kubernetes Kompose

- Tutorials/Documentation
  - [ ] Basic Overview
  - [ ] Explantion of Functions
  - [ ] Explantion of Configuration

### Screenshots
{{< figure src="/images/image_1.png" width="800" alt="Starlette" >}}
{{< figure src="/images/image_2.png" width="800" alt="Starlette" >}}
{{< figure src="/images/image_3.png" width="800" alt="Starlette" >}}
{{< figure src="/images/image_4.png" width="800" alt="Starlette" >}}
