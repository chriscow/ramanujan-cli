
## Prerequisites
- Install [docker for OSX](https://docs.docker.com/docker-for-mac/install/)

## Get into a Ramanujan shell
Make sure you are in the project directory, then run the following:

`docker-compose run --rm ramanujan bash`

This will start up the dependent services and give you a terminal prompt.

You are ready to go.   The rest in the doc are just notes and details.

## To generate the hashtable

To generate hashtable values based on the current configuration:

`python main.py generate [--lhs] [--rhs]`

`--lhs` and `--rhs` are optional flags to only generate the indicated side.

To search for key matches in the hashtable between the left and right hand sides:

`python main.py search`


## Running the containers
Simply run the following:

`docker-compose build`

`docker-compose up`

You can see the rq dashboard by visiting `http://localhost:9181`.

To stop the services, in another terminal window run:

`docker-compose down`

If you update the code that the workers depend on, such as algorithms.py or jobs.py
you will need to restart the services with:

`docker-compose restart`

## Getting a local python environment shell
`docker run -ti --rm -v $(pwd):/usr/share/src --expose 6379 --network ramanujan-cli_default ramanujan:latest /bin/bash`


## Some commands you can paste into the shell for a quick test

`python -c "from redis import Redis; from rq import Queue; import utils; import time; q = Queue(connection=Redis(host='redis')); utils.polynomial_to_string((3,4,5),6);"`

`python -c "from redis import Redis; from rq import Queue; import utils; import time; q = Queue(connection=Redis(host='redis')); print(utils.polynomial_to_string((3,4,5),6)); job = q.enqueue(utils.polynomial_to_string, (3,4,5),6); print(job.get_status()); time.sleep(2); print(job.result); print(job.get_status())"`

## RQ Single Worker
rq worker -c workers.settings --disable-job-desc-logging

## SSH Tunnel
ssh -L local_port:remote_address:remote_port username@server.com

## SSH Tunnel to Redis Cluster
ssh -i "ramanujan.pem" -L 7000:ramanujan.afnsuz.clustercfg.usw2.cache.amazonaws.com:6379 ec2-user@ec2-34-219-94-177.us-west-2.compute.amazonaws.com

## SSH Tunnel to Redis on Worker
ssh -i "ramanujan.pem" -L 6379:ec2-52-40-241-30.us-west-2.compute.amazonaws.com:6379 ec2-user@ec2-34-219-94-177.us-west-2.compute.amazonaws.com

## Redis command line
redis-server --bind 0.0.0.0 --appendonly no --save ""

## How to Screen
https://linuxize.com/post/how-to-use-linux-screen/

screen -S redis
redis-server
ctrl+a, d  (detach)
screen -ls

screen -r redis

# RQ Handy Commands
rq --help
rq empty --all -c workers.settings          Empty all queues
rq info --interval 1 -c workers.settings    Monitor every 1 second
rq suspend -c workers.settings              Suspends all workers 'rq resume' to start again

## TODO

- go back to using 0-* and 1-*.  We will have fewer keys for LHS for faster scanning
- after above do a keys '*', chunk up the keys and queue them out
- save key and lrange index for item that matches
- iterate over matching keys
