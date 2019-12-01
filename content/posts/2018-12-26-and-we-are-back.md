---
title: "And We Are Back..."
date: 2018-12-26T22:39:11-05:00
description: "Enter something here"
author: "Mike "
category: ["development","other"]
tags: ["Python","Random", "GO"]
draft: false
featured_image: "../images/Kilkee1.jpg"

---
{{< figure src="/image/broken-site.jpg" alt="I broke the internet." >}}
So I broke my last site (or two). I had been using Wordpress and decided I wanted something light weight. So I started playing with [Ghost](https://ghost.org/) and eventually had it running on my [Docker](https://www.docker.com/) instance. Initially I had it setup to learn and test, while also using it as my blog. Then I ran into a lot of issues... way more than you should run into when learning/building a blog.

Then I thought, why not just build my own... then I rethought that idea. It is a lot of work to keep a site secure. Constant upgrades to watch out for security flaws... on a low use site for my own entertainment... Maybe that is a bad idea.

What cannot be hacked? A static site running in a docker container. So I decided that it was best to just use a static site generator. So I tried a few and looked at even more.

* [Pelican](https://getpelican.com/) - nice, but painful to get going and it has a lot of dead themes around it. It was the best Python based I tried.
* [Lektor](https://www.getlektor.com/) - I like the admin interface, but there isn't much of a community from what I could tell. Still pretty good, but needs a community.
* [Hugo](https://gohugo.io/) - What I have decided to move forward with. It has a community and the learning curve was ok.

In the end, a static site generator is all I need. It also makes it simple to just keep a copy of the posts and pages. No DB connection or upgrade issues. Just rebuild.

Hugo is built with [GO](https://golang.org/), so maybe I will look into learning more about it. The templating is similar to [Jinja](http://jinja.pocoo.org/), so that looks interesting to learn more about.

##### **Slán**