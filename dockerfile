FROM python:3.11-alpine

WORKDIR /usr/src/app

RUN pip install --no-cache-dir docker, paramiko, schedule, dacite, fastapi, uvicorn

COPY ./src  /usr/src/app

CMD [ "python", "scheduler.py" ]