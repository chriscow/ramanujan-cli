import os, time
import click        # command line tools
import commands
import dotenv
import redis
import jobs
from datetime import datetime, timedelta
from subprocess import Popen, DEVNULL

@click.group()
def cli():
    pass


def check_environment():
    '''
    Loads environment variables from the local .env file.  If it doesn't exist
    it creates it with default localhost values.
    '''
    dotenv.load_dotenv()

    if os.getenv('RHS_DB') is None:
        print('Creating default .env file ...')
        with open('.env', 'w') as env:
            env.writelines('''REDIS_HOST=localhost
REDIS_PORT=6379

CELERY_BROKER_URL='redis://localhost:6379/15'
CELERY_BACKEND_URL='redis://localhost:6379/15'

WORK_QUEUE_DB=15
CONFIG_DB=14
LHS_DB=1
RHS_DB=0
            ''')

    dotenv.load_dotenv()
    assert(os.getenv('RHS_DB') is not None)


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

    # This doesn't work:
    # from celery import Celery
    # app = Celery()
    # app.config_from_object('celeryconfig')
    # app.control.ping(timeout=1)

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
            '\tcelery -A jobs worker -l INFO'])


if __name__ == '__main__':
    
    check_environment()
    check_redis_server()
    check_worker_status()

    cli.add_command(commands.generate)
    cli.add_command(commands.search)
    cli.add_command(commands.clean)
    cli()

