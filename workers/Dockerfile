FROM python:3

# Install Python dependencies
RUN pip install rq
RUN pip install supervisor

RUN mkdir /app
COPY . /app
WORKDIR /app

RUN pip install pipenv
RUN pipenv install --system --deploy --ignore-pipfile

# Spawn workers according to config
ENTRYPOINT ["/bin/bash", "-c", "supervisord -c /app/workers/supervisord.conf -n"]