# syntax=docker/dockerfile:1

FROM python:3.8-slim-buster

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .
CMD ["python3", "sunny_jim_webapp/manage.py", "runserver"]
