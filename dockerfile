FROM nginx:alpine
COPY /public /usr/share/nginx/html
EXPOSE 80
# ENV virtualhost=value
ENV VIRTUAL_HOST=devsetgo.com
ENV LETSENCRYPT_HOST=devsetgo.com
ENV LETSENCRYPT_EMAIL=mrstu@live.com
MAINTAINER Mike Ryan mrstu@live.com