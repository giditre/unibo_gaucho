FROM tiangolo/uwsgi-nginx-flask:python3.10

# If STATIC_INDEX is 1, serve / with /static/index.html directly (or the static URL configured)
ENV STATIC_INDEX 1
# ENV STATIC_INDEX 0

COPY ./app /app

WORKDIR /usr/src/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# RUN apk update   # not needed if you specify the repo with -X
# RUN apk add --no-cache -X http://dl-cdn.alpinelinux.org/alpine/edge/testing py3-flask-restful
#RUN apk update \
#    && apk add --virtual build-deps gcc python3-dev musl-dev \
#    && apk add postgresql \
#    && apk add postgresql-dev \
#    && pip install psycopg2 \
#    && apk add jpeg-dev zlib-dev libjpeg \
#    && pip install Pillow \
#    && apk del build-deps
#RUN pip install Werkzeug
# RUN apk add --no-cache -X http://dl-cdn.alpinelinux.org/alpine/edge/testing py3-flask-qrcode
