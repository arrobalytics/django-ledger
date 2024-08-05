FROM python:latest

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN apt-get update

RUN pip3 install --upgrade pip

RUN pip3 install -U pipenv

COPY . /app/

RUN pipenv install

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]