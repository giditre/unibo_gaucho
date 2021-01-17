FROM tiangolo/uwsgi-nginx-flask:python3.8-alpine

# If STATIC_INDEX is 1, serve / with /static/index.html directly (or the static URL configured)
ENV STATIC_INDEX 1
# ENV STATIC_INDEX 0

COPY ./app /app

# RUN apk update   # not needed if you specify the repo with -X
RUN apk add --no-cache -X http://dl-cdn.alpinelinux.org/alpine/edge/testing py3-flask-restful
# RUN apk add --no-cache -X http://dl-cdn.alpinelinux.org/alpine/edge/testing py3-flask-qrcode
