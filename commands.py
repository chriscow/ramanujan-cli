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

from data.wrapper import HashtableWrapper

from rediscluster import RedisCluster

import data.generate
import data.search
import data.save

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

formatter = utils.CustomConsoleFormatter()

@click.command()
def status():
    redis_conn = Redis(host=os.getenv('REDIS_HOST') , db=os.getenv('WORK_QUEUE_DB'))
    q = Queue(connection=redis_conn)

    count = q.count
    total = count

    while count > 0:
        utils.printProgressBar(total - count, total, prefix=f'Processing {total - count} of {total}')
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
    
    dbsize = 0
    dbsizes = source.dbsize()
    for key in dbsizes.keys():
        dbsize += dbsizes[key]

    dest = Redis(host=os.getenv('REDIS_HOST') , db=os.getenv('WORK_QUEUE_DB'))
    pipe = dest.pipeline(transaction=False)

    index = 0
    for keys in source.scan_iter():
        for key in keys:
            pipe.set(key, source.get(key))
            index += 1

        if len(keys):
            pipe.execute()    
            
        utils.printProgressBar(index, dbsize)


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
    for find in config.verify_finds:
        verify('lhs', eval(find), f'frac({find})')
    for find in config.verify_finds:
        verify('rhs', eval(find), f'frac({find})')   

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
    logging.basicConfig(filename='generate.log')

    start = datetime.now()  # keep track of what time we started
    log.info(f'[generate] rhs:{rhs} lhs:{lhs} started at {start}')

    # If neither rhs or lhs options were selected, choose both by default
    if not rhs and not lhs:
        rhs = True
        lhs = True

    if rhs: # generate the work items for the right hand side
        print('')
        print('\nGENERATE RHS')

        if os.getenv('RHS_KEY') is None:
            raise Exception('RHS_KEY environment variable is None')

        data.generate.run(config.rhs, os.getenv('RHS_KEY'), False, sync, silent)

        for find in config.verify_finds:
            verify('rhs', eval(find), f'frac({find})')


    if lhs: # generate the work items for the left hand side
        print('')
        print('\nGENERATE LHS')

        if os.getenv('LHS_KEY') is None:
            raise Exception('LHS_KEY environment variable is None')

        data.generate.run(config.lhs, os.getenv('LHS_KEY'), True, sync, silent)

        for find in config.verify_finds:
            verify('lhs', eval(find), f'frac({find})')

    log.info(f'Generation complete in {datetime.now() - start}')
    print('')

def verify(side, value, what):
    db = HashtableWrapper(side)
    value = mpmath.mpf(value)
    key = db.manipulate_key(mpmath.frac(value))
    keys = db.redis.keys(key)
    assert len(keys), f'Expected to find {what} {key} keys:{keys} {db.redis.connection} clustered:{db.clustered}'

@click.command()
def save():
    for find in config.verify_finds:
        verify('lhs', eval(find), f'frac({find})')
    for find in config.verify_finds:
        verify('rhs', eval(find), f'frac({find})')   
        
    data.save.run()

