---
title: "Python Async"
author: "Mike 'Stu' Ryan"
date: 2019-02-02T18:26:39-05:00
description: "Learning Python Asycnio and AioHTTP client"
category: ["python","development", "camunda"]
tags: ["python","async", "rest","example"]
draft: false
featured_images: "../images/Kilkee1.jpg"
---
<br>
I have been trying to learn [Python async and await](https://docs.python.org/3/library/asyncio.html). It is a great concept, but also a different way of programming. The image below is a visual of what asynchronous vs synchronous calls are. The advantage is gained if there is a wait for a response like in a REST call, where you are waiting on the server to respond. The idea is to let the application release the thread, perform some other action, then come back to the call when it returns.

{{< figure src="/images/async/asyncVsync.png" alt="asynchronous vs synchronous" >}}

Even though I am still working through how to make async calls, I made an example and came up with a simple idea on how to start using async while I am learning it. I built a simple example of fetching a list of tasks and then asynchronous calls to fetch the list of URLs being passed. Here is the [example on Github](https://github.com/devsetgo/async-example). No promises that any of that code is the right way to do async or frankly will even work.

Some interesting metrics on this experiment.
<ul>
    <li>synchronous rate is about 5 per second</li>
    <li>asynchronous rate is ranged from 480 to 785 in various tests</li>
    <li>setting a [connection limit of 150](https://docs.aiohttp.org/en/stable/client_advanced.html#client-session) was the optimal number and averaged around 720 per second</li>
    <li>100,000 calls took about 146 seconds (100,00/146 = 684)</li>
</ul>
Overall gain is well worth the use of Async in Python. I was using [AIOHTTP](https://docs.aiohttp.org) as the client call and my Camunda 7.10 instance (single node, H2 DB fetching the [task get](https://docs.camunda.org/manual/7.10/reference/rest/task/get-query/) api then looping through [each id](https://docs.camunda.org/manual/7.10/reference/rest/task/get/) to fetch that information)

If you use my code, please do not hit my server.

##### **Slán**