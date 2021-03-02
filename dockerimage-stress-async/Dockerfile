FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-alpine3.10

COPY ./app /app

RUN apk add stress-ng

# ENV LOG_LEVEL debug
# ENV WORKERS_PER_CORE 2
# ENV TIMEOUT 0
# ENV GRACEFUL_TIMEOUT 0