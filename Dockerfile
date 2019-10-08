# docker run -ti --rm -v $(pwd):/usr/share/src --expose 6379 --network ramanujan-cli_default ramanujan:latest /bin/bash

# without networking
# docker run -ti --rm -v $(pwd):/usr/share/src --expose 6379 ramanujan:latest /bin/bash

FROM python:3

ENV TERM=xterm-256color
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV REDIS_DB=0
ENV RQ_QUEUE=default
ENV LOG_LEVEL=DEBUG
ENV PIP_PACKAGES=none
ENV PIP_REQUIREMENTS=none
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8


RUN apt-get -q update >/dev/null \
    && apt-get install -y python3 python3-dev nano curl build-essential git supervisor redis-server \
    && curl https://bootstrap.pypa.io/get-pip.py | python3 \
    && curl https://bootstrap.pypa.io/get-pip.py | python \
    # Cleanup
    && apt-get clean autoclean \
    && apt-get autoremove --yes \
    && rm -rf /var/lib/{apt,dpkg,cache,log}/


RUN mkdir /ramanujan-cli
COPY . /ramanujan-cli
WORKDIR /ramanujan-cli

RUN pip3 install pipenv
RUN pipenv install --system --deploy --ignore-pipfile
