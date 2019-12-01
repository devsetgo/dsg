---
title: "Python FastAPI Library"
author: "Mike "
date: 2019-04-20T12:00:00-00:00
description: "Python FastAPI Library"
category: ["python","development"]
tags: ["python","FastAPI","Starlette","Asyncio"]
draft: false
featured_images: "../images/Kilkee1.jpg"
---
{{< figure src="/images/fastapi.png" width="600" alt="FastAPI" >}}

Over the last few months I have been learning Python's [Asyncio](https://docs.python.org/3/library/asyncio.html) library. It came from a need at work. I needed to pull a large about of data from Sonarqube. The data is broke into pages of 500 issues each and it required about 50 calls to retrieve all the issues. Using Requests this took about 8-10 minutes via synchronous calls. Each page load being 4-8 seconds and the data processing at the end (about 10 seconds). Frankly, I wasn't expecting this long time to get the data back and decided it was a perfect use for Asyncio.

{{< figure src="/images/async/asyncVsync.png" width="600" alt="Asyncio" >}}

I find it difficult to explain Asynchronous vs Synchronous programming. Simplest explanation is that the program drops everything into a loop and while it waits for the response it can do "something else". Like make another call or work on the response. [Michael Kennedy](https://blog.michaelckennedy.net/) has some great [tutorials](https://blog.jetbrains.com/pycharm/2019/02/webinar-recording-demystifying-pythons-async-and-await-keywords-with-michael-kennedy/) on this topic, I suggest [reviewing his courses](https://training.talkpython.fm/courses/explore_async_python/async-in-python-with-threading-and-multiprocessing).

I played with several Async frameworks and also tried writting basic "async" and "await" functions to get better at the concept. I my main goal was an API builder and "if" possible also build frontend sites with it.

- **[Flask with Celery](http://flask.pocoo.org/docs/1.0/patterns/celery/)**: Not actually an async framework, but a way to run on another thread. I found this really cool, but a lot of overhead with needing RabbitMQ or Redis.
- **[Quart](https://gitlab.com/pgjones/quart)**: This is a great idea. Flask that is Async, but not all of Flask is there. There are a lot of issues with existing libraries. Flask-RestPlus doesn't work with it. I hope this becomes Flask Async... it has great promise.
- **[Aiohttp](https://aiohttp.readthedocs.io/en/stable/)**: This is how I solved the sonarqube report data issue at work. I find it harder to get into, but the client side was easiest.
- **[Sanic](https://sanicframework.org/)**: This is interesting, but I am less focused on "pure speed" and more on ability to build out an API or application. It has good documentation, but I just never really got into Sanic.
- **[FastAPI](https://fastapi.tiangolo.com/)**: I stumbled on this while looking at [Starlette](https://github.com/encode/starlette)/[Responder](https://github.com/kennethreitz/responder). I found it to be easy to get into, easy to learn, and really quick to build out basic APIs. Since it is built over Starlette I can still build a frontend and stay within a single framework (starlette).

Over the last few weeks, I have been learning FastAPI and building a test api to simulate long waits. Just like my original problem above. I took inspiration from [FakeResponse.com](http://www.fakeresponse.com/) and would like to build the test api out more to fit more of my needs. You can find more information at the page for the [Test API](https://devsetgo.com/projects/test-api/) project.

As a note, I seem to hit a maximum threshold of ~2100 calls per second with Async on my notebook. I think this may be a limit of Python on a single thread. SSL on tends to reduce this by about 50% as the extra hope to confirm the cert. Running the benchmarks via [WRK](https://github.com/wg/wrk) I am getting about 500 requests per second. I still need to work on performance and it is using a SQLite db, so I think it is reasonable.

I used this [tutorial for WRK](https://medium.com/pharos-production/how-to-benchmark-http-latency-with-wrk-a-z-guide-e5b185bd4cdc) and I ran the command as below (please don't use my server for your tests, just pull the docker image and run it on your server) and it worked.

~~~~
docker run --rm williamyeh/wrk -t2 -c5 -d5s https://test-api.devsetgo.com/api/v1/todo/list/count --timeout 2s
~~~~


##### **Slán**
