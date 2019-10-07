FROM python:3

# Install Python dependencies
RUN pip3 install rq
RUN pip3 install supervisor

RUN mkdir /app
COPY . /app
WORKDIR /app

RUN pip3 install pipenv
RUN pipenv install --system --deploy --ignore-pipfile

# Spawn workers according to config
ENTRYPOINT ["/bin/bash", "-c", "supervisord -c /app/workers/supervisord.conf -n"]