FROM python:3.11-alpine

WORKDIR /usr/src/app

RUN pip install --no-cache-dir docker
RUN pip install --no-cache-dir paramiko
RUN pip install --no-cache-dir schedule
RUN pip install --no-cache-dir dacite

COPY ./src  /usr/src/app

CMD [ "python", "scheduler.py" ]