---
title: "Pynote"
date: 2019-08-16T00:00:00-01:00
draft: false
description: "A template for Flask using Sufee Admin Bootstrap template."
featured_image: "../images/pynote-0-1-2.png"

---
{{< figure src="/images/pynote-0-1-2.png" width="600" alt="Pynote" >}}
Journal, Idea Tracker and Other things. This application is based and built off [Flask-AppBuilder](https://github.com/dpgaspar/Flask-AppBuilder) by [dpgaspar](https://github.com/dpgaspar)


-------------------------------------------------------------
## Run the application from OS
Prerequisits
* Python (3.5)
* virtualenv

Run the application
* create a virtual environment - virtualenv env
* Install Requirements in Virtual Environment - pip install -r requirements.txt
* fabmanger create-admin
    - Follow instructions
* fabmanger Run
    - Application is now running
    - Test and modify code as you want

----------------------------------------------------------
## Run the Application with Docker
----------------------------------------------------------
### Demo version
* Docker Pull mikeryan56/pynote_demo:latest
* demo db
    - username: admin
    - password: $Password
* or clone and run (gunicorn -c gunicorn_cfg.py app:app)

----------------------------------------------------------
### Regular version
: To be built later