
## Prerequisites
- Install [docker for OSX](https://docs.docker.com/docker-for-mac/install/)

## Running the containers
Simply run the following:

`docker-compose build`

`docker-compose up`

You can see the rq dashboard by visiting `http://localhost:9181`.

To stop the services, in another terminal window run:

`docker-compose down`


## Getting a local python environment shell
`docker run -ti --rm -v $(pwd):/usr/share/src --expose 6379 --network ramanujan-cli_default ramanujan:latest /bin/bash`


## Some commands you can paste into the shell for a quick test

`python -c "from redis import Redis; from rq import Queue; import utils; import time; q = Queue(connection=Redis(host='redis')); utils.polynomial_to_string((3,4,5),6);"`

`python -c "from redis import Redis; from rq import Queue; import utils; import time; q = Queue(connection=Redis(host='redis')); print(utils.polynomial_to_string((3,4,5),6)); job = q.enqueue(utils.polynomial_to_string, (3,4,5),6); print(job.get_status()); time.sleep(2); print(job.result); print(job.get_status())"`