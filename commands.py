import os, time, itertools
from datetime import datetime, timedelta
import click
import logging

from redis import Redis
from rq import Queue

import mpmath
from mpmath import mpf, mpc

import config
import jobs
import utils    

from rediscluster import RedisCluster

import data.generate
import data.search
import data.save

log = logging.getLogger(__name__)

@click.command()
def status():
    redis_conn = Redis(host=os.getenv('REDIS_HOST') , db=os.getenv('WORK_QUEUE_DB'))
    q = Queue(connection=redis_conn)

    count = q.count
    total = count

    while count > 0:
        utils.printProgressBar(total - count, total, prefix=f'Processing {total - count} of {total}', suffix='          ')
        time.sleep(1)
        count = q.count

@click.command()
def migrate():
    if os.getenv('REDIS_CLUSTER_HOST'):
        startup_nodes = [{"host": os.getenv('REDIS_CLUSTER_HOST'), "port": os.getenv('REDIS_CLUSTER_PORT')}]
        try:
            source = RedisCluster(startup_nodes=startup_nodes, decode_responses=True, skip_full_coverage_check=True)
        except:
            print('Did you be sure to ' + utils.bcolors.OKBLUE + 'export REDIS_CLUSTER_IP=0.0.0.0' + utils.bcolors.ENDC)
    else:
        source = Redis(os.getenv('REDIS_HOST'), os.getenv('REDIS_PORT'))
        
    dest = Redis(host=os.getenv('REDIS_HOST') , db=os.getenv('WORK_QUEUE_DB'))
    pipe = dest.pipeline(transaction=False)

    for keys in source.scan_iter():
        for key in keys:
            pipe.set(key, source.get(key))

        pipe.execute()    
        


@click.command()
def clear():

    # Check for local redis or cluster
    if os.getenv('REDIS_CLUSTER_HOST'):
        startup_nodes = [{"host": os.getenv('REDIS_CLUSTER_HOST'), "port": os.getenv('REDIS_CLUSTER_PORT')}]
        try:
            redis = RedisCluster(startup_nodes=startup_nodes, decode_responses=True, skip_full_coverage_check=True)
        except:
            print('Did you be sure to ' + utils.bcolors.OKBLUE + 'export REDIS_CLUSTER_IP=0.0.0.0' + utils.bcolors.ENDC)
    else:
        redis = Redis(os.getenv('REDIS_HOST'), os.getenv('REDIS_PORT'))
        
    redis.flushdb()

    redis_conn = Redis(host=os.getenv('REDIS_HOST') , db=os.getenv('WORK_QUEUE_DB'))
    q = Queue(connection=redis_conn)
    q.empty()

    print(f'Cluster data cleared.  Work queue emptied.')


@click.argument('precision', nargs=1, default=50)
@click.option('--sync', is_flag=True, default=False)
@click.option('--silent', '-s', is_flag=True, default=False)
@click.command()
def search(precision, sync, silent):
    '''
    We want to:
        - make a first pass and find all key matches between the two sides
        - with all matches, 
    '''
    data.search.run(precision, sync, silent)



@click.option('--rhs', '-r', is_flag=True, default=False, help='Generate only the right hand side data')
@click.option('--lhs', '-l', is_flag=True, default=False, help='Generate only the left hand side data')
@click.option('--sync', '-s', is_flag=True, default=False, help='Runs synchronously without queueing')
@click.option('--log-level', default='logging.DEBUG', help='Sets the logging level. Use: logging.DEBUG | logging.WARN etc.')
@click.option('--silent', is_flag=True, default=False)
@click.command()
def generate(rhs, lhs, sync, log_level, silent):
    '''
    This command takes the configured coefficient ranges and divides them up
    for separate processes to work on the smaller chunks.  Each chunk is saved
    in a work queue and the workers pull from that queue until its empty.

    Those workers post their results directly to the data.
    '''
    logging.basicConfig(filename=f'generate.log',level=eval(log_level))

    start = datetime.now()  # keep track of what time we started
    log.info(f'[generate] rhs:{rhs} lhs:{lhs} started at {start}')

    # If neither rhs or lhs options were selected, choose both by default
    if not rhs and not lhs:
        rhs = True
        lhs = True

    if rhs: # generate the work items for the right hand side
        print()
        print('\nGENERATE RHS')

        if os.getenv('RHS_KEY') is None:
            raise Exception('RHS_KEY environment variable is None')

        data.generate.run(config.rhs, os.getenv('RHS_KEY'), False, sync, silent)

    if lhs: # generate the work items for the left hand side
        print()
        print('\nGENERATE LHS')

        if os.getenv('LHS_KEY') is None:
            raise Exception('LHS_KEY environment variable is None')

        data.generate.run(config.lhs, os.getenv('LHS_KEY'), True, sync, silent)

    print()

@click.command()
def save():
    data.save.run()

