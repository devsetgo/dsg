---
title: "Cookiecutter-Flask-SBAdmin"
date:  2019-08-16T00:00:00-04:00
draft: false
---

{{< figure src="/images/cookiecutter-flask-sbadmin/sshot-1.png" width="600" alt="cookiecutter-flask-sbadmin" >}}
A Flask template for cookiecutter using [SB Admin Bootstrap](https://startbootstrap.com/template-overviews/sb-admin/) template. Forked from [CookieCutter-Flask](https://github.com/sloria/cookiecutter-flask) at version 0.12.0.

This is to have a simpler version using SB Admin as I don't want NPM or Bower as part of my apps.

Tested with modern Python (3.5 and higher).

Built with [cookiecutter](https://github.com/audreyr/cookiecutter)

## ToDo
* Make docker ready deployments
* Deploy a running example on Docker
* Clean up of resources to remove unused/needed functionality

## Give it a try!
<blockquote>
    <ul>
        <li>$ docker pull <a href="https://cloud.docker.com/u/mikeryan56/repository/docker/mikeryan56/flask-sbadmin" target="_blank">MikeRyan56/flask-sbadmin:latest</a></li>
        <!-- <li>Running Demo - <a href="https://sbadmin.devsetgo.com" target="_blank">sbadmin.devsetgo.com</a></li> -->
    <ul>
</blockquote>

## Use it now
----------
<blockquote>
    <ul>
        <li>$ virtualenv env</li>
        <li>$ env\scritps\activate (Windows) or source env/bin/activate (linux)</li>
        <li>$ pip install cookiecutter</li>
        <li>$ cookiecutter https://github.com/devsetgo/Cookiecutter-Flask-SBAdmin.git</li>
    <ul>
</blockquote>
You will be asked about your basic info (name, project name, app name, etc.). This info will be used in your new project.

Setup your app
<blockquote>
    <ul>
        <li>$ cd <your app directory> </li>
        <li>$ pip install -r requirements.txt (or requirements/dev.txt)</li>
        <li>$ flask db init</li>
        <li>$ flask db migrate</li>
        <li>$ flask db upgrade</li>
        <li>$ flask run</li>
    </ul>
</blockquote>
You should see the app runing. Create a New Account and login. You should have access to the whole application.

## Features
--------

- Bootstrap 4 and Font Awesome 5 with starter templates
- Flask-SQLAlchemy with basic User model
- Easy database migrations with Flask-Migrate
- Flask-WTForms with login and registration forms
- Flask-Login for authentication
- Flask-Bcrypt for password hashing
- Procfile for deploying to a PaaS (e.g. Heroku) (will leave, but I don't use it)
- pytest and Factory-Boy for testing (example tests included)
- Flask's Click CLI configured with simple commands
- CSS and JS minification using Flask-Assets (will remove)
- Optional bower support for frontend package management
- Caching using Flask-Caching
- Useful debug toolbar
- Utilizes best practices: [Blueprints](http://flask.pocoo.org/docs/blueprints/) and [Application Factory](http://flask.pocoo.org/docs/patterns/appfactories/) patterns

Screenshots
-----------

{{< figure src="/images/cookiecutter-flask-sbadmin/sshot-1.png" width="600" alt="Front page" >}}
{{< figure src="/images/cookiecutter-flask-sbadmin/sshot-2.png" width="600" alt="Registration Page" >}}
{{< figure src="/images/cookiecutter-flask-sbadmin/sshot-3.png" width="600" alt="Members Page" >}}
{{< figure src="/images/cookiecutter-flask-sbadmin/sshot-4.png" width="600" alt="Charts Page" >}}
{{< figure src="/images/cookiecutter-flask-sbadmin/sshot-5.png" width="600" alt="Tables Page" >}}


Inspiration
-----------
- [CookieCutter-Flask](https://github.com/sloria/cookiecutter-flask) by [Steven Loria](https://github.com/sloria) as the base of this repo
- [Building Websites in Python with Flask](http://maximebf.com/blog/2012/10/building-websites-in-python-with-flask/)
- [Getting Bigger with Flask](http://maximebf.com/blog/2012/11/getting-bigger-with-flask/)
- [Structuring Flask Apps](http://charlesleifer.com/blog/structuring-flask-apps-a-how-to-for-those-coming-from-django/)
- [Flask-Foundation](https://github.com/JackStouffer/Flask-Foundation) by [@JackStouffer](https://github.com/JackStouffer)
- [flask-bones](https://github.com/cburmeister/flask-bones) by [@cburmeister](https://github.com/cburmeister)
- [flask-basic-registration](https://github.com/mjhea0/flask-basic-registration) by [@mjhea0](https://github.com/mjhea)
- [Flask Official Documentation](http://flask.pocoo.org/docs/)

