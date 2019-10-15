import os, time
import click        # command line tools
import commands
import dotenv
import redis, rq
import jobs
from datetime import datetime, timedelta
from subprocess import Popen, DEVNULL
from multiprocessing import cpu_count

#
# The stuff in this main.py file is just to handle command line arguments
# and check to see if the dependent programs are running (celery worker, redis-server)
#

# ssh -i "ramanujan.pem" -L 6379:ramanujan.afnsuz.0001.usw2.cache.amazonaws.com:6379 ec2-user@ec2-52-38-8-180.us-west-2.compute.amazonaws.com

@click.group()
def cli():
    pass


def check_environment():
    '''
    Loads environment variables from the local .env file.  If it doesn't exist
    it creates it with default localhost values.
    '''
    dotenv.load_dotenv()

    #if os.getenv('DOCKER') is None:
    #    os.environ['REDIS_HOST'] = 'localhost'

    if os.getenv('RHS_KEY') is None:
        print('Creating default .env file ...')
        with open('.env', 'w') as env:
            env.writelines('''REDIS_CLUSTER_HOST=ramanujan.afnsuz.clustercfg.usw2.cache.amazonaws.com
REDIS_CLUSTER_PORT=6379

REDIS_HOST=127.0.0.1
REDIS_PORT=6379

WORK_QUEUE_DB=15
CONFIG_DB=14
LHS_KEY=lhs
RHS_KEY=rhs
            ''')

    dotenv.load_dotenv()
    assert(os.getenv('RHS_KEY') is not None)


def print_error_and_exit(lines):
    print('-')
    print('-' * 75)
    print('-')
    for line in lines:
        print(f'- {line}')
    print('-')
    print('-' * 75)
    print('')
    exit()

def check_redis_server():
    '''
    Verifies that the redis server is running and we can connect to it.
    '''
    try:
        db = redis.Redis(host=os.getenv('REDIS_HOST'),  port=os.getenv('REDIS_PORT'), db=os.getenv('CONFIG_DB'))
        if not db.ping():
            raise 
    except:
        print_error_and_exit([f'Cannot connect to the redis server at {os.getenv("REDIS_HOST")}.',
        'You can run it locally by opening a new terminal window.',
        'Make sure you are in the project directory and run:',
        '',
        '\tredis-server'])


def check_worker_status():
    '''
    Queues the 'ping' job.  If celery workers are running it will succeed.
    '''

    job_started = datetime.now()
    job = jobs.ping.delay(job_started)

    job_timeout = timedelta(seconds=1)
    
    while not job.ready():
        time.sleep(.1)            
        elapsed = datetime.now() - job_started

        if elapsed > job_timeout:
            print_error_and_exit(['No running Celery workers were found.',
            'Open a new terminal window and be sure you are in the project directory,',
            'and run:',
            '',
            f'\tcelery -A jobs worker -l info --concurrency {cpu_count() - 2}'])



if __name__ == '__main__':

    check_environment()

    cli.add_command(commands.status)
    cli.add_command(commands.clear)
    cli.add_command(commands.generate)
    cli.add_command(commands.search)
    cli.add_command(commands.save)
    cli.add_command(commands.migrate)
    cli()
