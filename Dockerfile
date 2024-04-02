FROM python:latest

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN apt-get update

RUN pip3 install --upgrade pip

RUN pip3 install -U pipenv

COPY Pipfile Pipfile.lock /app/

COPY . /app/

COPY entrypoint.sh /app/

RUN pipenv install

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]