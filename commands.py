import os, datetime, time
import click
import redis
import rq
import inspect
import dotenv

import mpmath
from mpmath import mpf

import algorithms
import config
import data
import jobs
import postproc
import utils

@click.option('--silent', '-s', is_flag=True, default=False)
@click.command()
def clean(silent):
    '''
    Deletes all data from redis to start from scatch.
    '''
    for i in range(0, 16):
        db = redis.Redis(host=os.getenv('REDIS_HOST'),  port=os.getenv('REDIS_PORT'), db=i)
        result = db.flushdb()

    if not silent:
        print('Redis data deleted')

def get_funcs(module):
    result = {}
    funcs = [fn for name,fn in inspect.getmembers(module) if inspect.isfunction(fn)]
    for fn in funcs:
        if hasattr(fn, 'type_id'):
            type_id = getattr(fn, 'type_id')
            result[type_id] = fn.__name__

    return result

@click.argument('filename')
@click.option('--silent', '-s', is_flag=True, default=False)
@click.command()
def search(filename, silent):

    lhs = data.DecimalHashTable(db=int(os.getenv('LHS_DB')))
    rhs = data.DecimalHashTable(db=int(os.getenv('RHS_DB')))

    lhs_size = lhs.redis.dbsize()
    rhs_size = rhs.redis.dbsize()

    postprocs = get_funcs(postproc)
    algos = get_funcs(algorithms)

    cur = 0
    with open(filename, 'w') as output:
        for key in lhs.redis.scan_iter():

            # rhs_vals is a list of algorithm parameters used to generate the result
            rhs_vals = rhs.redis.lrange(key, 0, -1)
            for rhs_val in rhs_vals:

                lhs_algo_id, lhs_postfn_id, constant, lhs_a_coeff, lhs_b_coeff = eval(lhs.redis.lrange(key, 0, 1)[0])
                rhs_algo_id, rhs_postfn_id, poly_range, rhs_a_coeff, rhs_b_coeff = eval(rhs_val)
                output.write('\n')
                output.write(f'LHS Key:{key} {algos[lhs_algo_id]} {postprocs[lhs_postfn_id]} {constant} {lhs_a_coeff} {lhs_b_coeff}\n')
                output.write(f'RHS: {algos[rhs_algo_id]} {postprocs[rhs_postfn_id]} {poly_range} {rhs_a_coeff} {rhs_b_coeff}\n')

            if not silent:
                cur += 1
                utils.printProgressBar(cur, lhs_size)




@click.option('--rhs', '-r', is_flag=True, default=False, help='Generate only the right hand side data')
@click.option('--lhs', '-l', is_flag=True, default=False, help='Generate only the left hand side data')
@click.option('--debug', '-d', is_flag=True, default=False, help='Runs synchronously without queueing')
@click.option('--silent', '-s', is_flag=True, default=False)
@click.command()
def generate(rhs, lhs, debug, silent):
    '''
    This command takes the configured coefficient ranges and divides them up
    for separate processes to work on the smaller chunks.  Each chunk is saved
    in a work queue and the workers pull from that queue until its empty.

    Those workers post their results directly to the hashtable.
    '''

    # If neither rhs or lhs options were selected, choose both by default
    if not rhs and not lhs:
        rhs = True
        lhs = True


    work = set()

    if not silent:
        print('')
        print('Queuing work ...')

    if rhs:
        jobs = _generate(config.rhs, int(os.getenv('RHS_DB')), False, debug, silent)
        work |= jobs

    if lhs:
        jobs = _generate(config.lhs, int(os.getenv('LHS_DB')), True, debug, silent)
        work |= jobs

    if not silent:
        print('')
        print(f'Waiting for {len(work)} jobs ...')
    
    wait(work, silent)

    for job in work:
        job.forget()  # free up the resources


def _generate(side, db, use_constants, debug=False, silent=False):

    precision  = config.hash_precision
    const_type = type(mpmath.e)

    algo   = side.algorithm.__name__

    a_range    = side.a_range
    b_range    = side.b_range
    poly_range = config.polynomial_range
    black_list = side.black_list
    
    work = set()

    if use_constants:
        count = 0
        for const in config.constants:
            # mpf is not serializable so convert to string
            const = mpf(const)
            jobs = queue_work(db, precision, algo, a_range, b_range, const, black_list, debug=debug)
            work |= jobs
            count += 1
            utils.printProgressBar(count, len(config.constants))
    else:
        work = queue_work(db, precision, algo, a_range, b_range, config.polynomial_range, black_list)

    return work


def queue_work(db, precision, algo_name, a_range, b_range, poly_range, black_list, debug=False):
    '''
    Queues the algorithm calculations to be run and stored in the database.
    '''
    batch_size = 100

    #total_work = algorithms.range_length(b_range, algorithms.range_length(a_range))

    count = 1
    a = []  # holds a subset of the coefficient a-range
    b = []  # holds a subset of the coefficient b-range
    work = set()  # set of all jobs queued up to know when we are done

    start = datetime.datetime.now()  # keep track of what time we started

    # Loop through all coefficient possibilities
    for a_coeff, b_coeff in algorithms.iterate_coeff_ranges(a_range, b_range):

        a.append(a_coeff)
        b.append(b_coeff)
        count += 1

        # When the list of a's and b's are up to batch_size, queue a job
        if count % batch_size == 0:
            # We are queuing arrays of coefficients to work on
            if debug:
                jobs.store(db, precision, algo_name, a, b, repr(poly_range), black_list)
            else:
                job = jobs.store.delay(db, precision, algo_name, a, b, repr(poly_range), black_list)
                work.add(job)   # hold onto the job info

            a = []
            b = []

    # If there are any left over coefficients whos array was not evenly
    # divisible by the batch_size, queue them up also
    if len(a):
        if debug:
            jobs.store(db, precision, algo_name, a, b, repr(poly_range), black_list)
        else:
            job = jobs.store.delay(db, precision, algo_name, a, b, repr(poly_range), black_list)
            work.add(job) 

    return work


def wait(work, silent):
    '''
    Waits on a set of celery job objects to complete. The caller is responsible
    for calling forget() on the result to remove it from the backend.

    Arguments:
        work - a Python set() object containing Celery AsyncResult instances

    Returns:
        All of the jobs passed in
    '''
    total_work = len(work)
    running = True

    while len(work):  # while there is still work to do ...

        utils.printProgressBar(total_work - len(work), total_work)

        completed_jobs = set()  # hold completed jobs done in this loop pass

        for job in work:
            
            if job.ready():
                completed_jobs.add(job)
                continue
            
        # print(f'completed:{len(completed_jobs)} failed:{len(failed_jobs)}')

        # Removes completed jobs from work
        work = work - completed_jobs
        time.sleep(.1)
    
    if not silent:
        utils.printProgressBar(total_work, total_work)
