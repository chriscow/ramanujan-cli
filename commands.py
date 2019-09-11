import os, time, itertools
from datetime import datetime, timedelta
import click

from redis import Redis
from rq import Queue

import mpmath
from mpmath import mpf, mpc

import config
import jobs
import utils    

import data.generate
import data.search

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


@click.argument('queue_name', nargs=1, default='default')
@click.command()
def clear(queue_name):
    redis_conn = Redis(host=os.getenv('REDIS_HOST') , db=os.getenv('WORK_QUEUE_DB'))
    q = Queue(queue_name, connection=redis_conn)

    q.empty()

    print(f'Work queue {q.name} cleared.')


@click.argument('precision', nargs=1, default=50)
@click.option('--debug', is_flag=True, default=False)
@click.option('--silent', '-s', is_flag=True, default=False)
@click.command()
def search(precision, debug, silent):
    '''
    We want to:
        - make a first pass and find all key matches between the two sides
        - with all matches, 
    '''
    data.search.run(precision, debug, silent)



@click.option('--rhs', '-r', is_flag=True, default=False, help='Generate only the right hand side data')
@click.option('--lhs', '-l', is_flag=True, default=False, help='Generate only the left hand side data')
@click.option('--debug', '-d', is_flag=True, default=False, help='Runs synchronously without queueing')
@click.option('--silent', is_flag=True, default=False)
@click.command()
def generate(rhs, lhs, debug, silent):
    '''
    This command takes the configured coefficient ranges and divides them up
    for separate processes to work on the smaller chunks.  Each chunk is saved
    in a work queue and the workers pull from that queue until its empty.

    Those workers post their results directly to the data.
    '''
    start = datetime.now()  # keep track of what time we started

    # If neither rhs or lhs options were selected, choose both by default
    if not rhs and not lhs:
        rhs = True
        lhs = True

    work = set()

    if rhs: # generate the work items for the right hand side
        work = data.generate.run(config.rhs, int(os.getenv('RHS_DB')), False, debug, silent)
        jobs.wait(work, silent)


    if lhs: # generate the work items for the left hand side
        work = data.generate.run(config.lhs, int(os.getenv('LHS_DB')), True, debug, silent)
        jobs.wait(work, silent)

    print()


