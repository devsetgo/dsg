---
title: "Using Spring Cloud Config with Python Requests"
author: "Mike "
date: 2019-04-22T12:00:00-00:00
description: "Using Spring Cloud Config with Python/Flask to set environment variables"
category: ["python","development","JAVA"]
tags: ["python","flask","spring cloud config", "twelve factor", "spring framework"]
draft: false
featured_images: "../images/Kilkee1.jpg"
---

{{< figure src="/images/spring-by-pivotal.png" width="600" alt="Spring Cloud Config" >}}

At work we use [Spring Cloud Config](https://spring.io/projects/spring-cloud-config) as part of are management of external dependencies for JAVA APIs. So I thought this would be useful to manage dependencies for Python applications also and an effective way of dealing with external environment variables when deploying a docker image as part of a [Twelve Factor App](https://12factor.net/).

Why is this important?

- You don't want to hardcode your configuration (keys, IP address, userid, passwords)
- Deploying .env files is better, but how to protect that data
- You should store keys and other items outside of the open repo for security
- Changing variables in a .env file requires a new release
- Deploying a Docker Image means others will have access to your secret information (Keys, passwords)

With Spring Cloud Config you just create YAML files in a Github, Gitlab or other repo. Then Cloud Config pulls (clones) that repo into it config directory. Then you access via a REST API.

{{< figure src="/images/scc.png" width="600" alt="Spring Cloud Config" >}}

Considering how easy it is to call an API in Python, this makes total sense to me as an effect method of managing external dependencies.

I am using a prebuilt Docker Image ([hyness/spring-cloud-config-server](https://hub.docker.com/r/hyness/spring-cloud-config-server/)) and I am still working through a few issues.

- I cannot use **SPRING_CLOUD_CONFIG_SERVER_GIT_URI** with a private repo (token or username/password). So I am using a volume that I have cloned my repo to. I have a issue at the github repo for Hyness and will see what my options are.
- Still need to make sure that the docker image is completely secure from the outside world
- If I cannot git pull via restarting the docker image, then I need to setup a git pull via chron to happen on a set interval (every hour/day, etc..) and in my login bash script.
- Organize the git repo... Looks like need a common structure (appname-environment.yml) in the main folder. Not a big deal, but still need to define a pattern
- Need to create a simple function to add into any Python app I build. Again easy, just need to standardize my approach.
- And also make sure I undertand this well with JAVA.
- Need to do more testing on my Docker Images, but I think this a reasonable way of managing external configurations.


##### **Slán**

