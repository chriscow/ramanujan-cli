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

log = logging.getLogger(__name__)

@click.command()
def status():
    redis_conn = Redis(host=os.getenv('REDIS_HOST') , db=os.getenv('WORK_QUEUE_DB'))
    q = Queue(connection=redis_conn)

    count = q.count
    total = count

    while count > 0:
        utils.printProgressBar(total - count, total, prefix=f'Processing {count} of {total}', suffix='          ')
        time.sleep(.1)
        count = q.count


@click.command()
def clear():
    startup_nodes = [{"host": os.getenv('REDIS_CLUSTER_HOST'), "port": os.getenv('REDIS_CLUSTER_PORT')}]
    redis = RedisCluster(startup_nodes=startup_nodes, decode_responses=True, skip_full_coverage_check=True)
    redis.flushall()

    print(f'Cluster data cleared.')


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

    work = set()

    state = Redis()

    if rhs: # generate the work items for the right hand side
        state.set('state.generate', 'rhs')
        print()
        print('\nGENERATE RHS')

        state.set('rhs.data.generate.run', 0)
        for work in data.generate.run(config.rhs, int(os.getenv('RHS_DB')), False, sync, silent):
            jobs.wait(work, silent)
            state.incr('rhs.data.generate.run')
        
        state.delete('rhs.data.generate.run')

    if lhs: # generate the work items for the left hand side
        state.set('lhs.data.generate', 'lhs')
        print()
        print('\nGENERATE LHS')

        state.set('lhs.data.generate.run', 0)
        for work in data.generate.run(config.lhs, int(os.getenv('LHS_DB')), True, sync, silent):
            jobs.wait(work, silent)
            state.incr('lhs.data.generate.run')
        
        state.delete('lhs.data.generate.run')
    
    state.delete('state.generate')

    print()


