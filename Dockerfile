# syntax=docker/dockerfile:1

FROM python:3.10.6-alpine

RUN apk update && apk upgrade
RUN apk add --no-cache sqlite gcc musl-dev libffi-dev openssl-dev python3-dev g++ postgresql-dev

WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app
RUN mkdir -p /app/config
RUN cp /app/config.yaml /app/config/config.yaml

CMD ["python3", "/app/sunny_jim.py", "--config", "/app/config/config.yaml"]
