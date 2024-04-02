FROM python:latest

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN apt-get update

RUN pip install --upgrade pip

RUN pip install -U pipenv

COPY Pipfile Pipfile.lock /app/

RUN pipenv install --system

COPY . /app/

COPY entrypoint.sh /app/

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]