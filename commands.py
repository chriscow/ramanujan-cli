import os, datetime, time
import click
import redis
import rq
import inspect
import dotenv

import multiprocessing as mp

import algorithms
import jobs
import utils

from config import *


@click.option('--silent', '-s', is_flag=True, default=False)
@click.command()
def search(silent):

    for job in completed:
        
        job.result
        if job.status == 'SUCCESS':

            if ht.get(result):
                val = ht.get(result)
                for algo_type, a, b in val:
                    if algo_type == algorithms.continued_fraction.type_id:
                        print('RHS:')
                        print(utils.polynomial_to_string(a_coeff, const))
                        print('-' * 50)
                        print(utils.polynomial_to_string(b_coeff, const))

                        print(utils.cont_frac_to_string(result, a, b))
                    else:
                        print(result, val)

@click.command()
def generate():
    '''
    This command takes the configured coefficient ranges and divides them up
    for separate processes to work on the smaller chunks.  Each chunk is saved
    in a work queue and the workers pull from that queue until its empty.

    Those workers post their results directly to the hashtable.
    '''
    dotenv.load_dotenv()

    precision  = hash_precision

    rhs_db = int(os.getenv('RHS_DB'))
    lhs_db = int(os.getenv('LHS_DB'))

    rhs_algo   = rhs.algorithm.__name__
    lhs_algo   = lhs.algorithm.__name__

    rhs_a_range    = rhs.a_range
    rhs_b_range    = rhs.b_range
    poly_range     = rhs.polynomial_range
    rhs_black_list = rhs.black_list
    
    lhs_a_range = lhs.a_range
    lhs_b_range = lhs.b_range

    print('Queuing rhs jobs...', end='')
    rhs_jobs = queue_work(rhs_db, precision, rhs.algorithm.__name__, 
        rhs.a_range, rhs.b_range, 
        rhs.polynomial_range, rhs.black_list)

    print(f'{len(rhs_jobs)}')

    print('Queuing lhs jobs...', end='')
    const_type = type(mpmath.e)

    for const in lhs.constants:
        # mpf is not serializable so convert to string
        const = str(const)

        print(f'------- starting const: {const}')
        lhs_jobs = queue_work(lhs_db, precision, lhs.algorithm.__name__, 
            lhs.a_range, lhs.b_range, 
            const, lhs.black_list, asynch=False)

    print(f'{len(lhs_jobs)}')
    print(f'Total queued jobs: {len(rhs_jobs | lhs_jobs)}')

    completed = wait(rhs_jobs | lhs_jobs)

    for job in completed:
        job.forget() # release results & resources held by job


def queue_work(db, precision, algo_name, a_range, b_range, poly_range, black_list, asynch=True):
    '''
    Queues the algorithm
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
            if asynch:
                job = jobs.store.delay(db, precision, algo_name, a, b, poly_range, black_list)
                work.add(job)   # hold onto the job info
            else:
                jobs.store(db, precision, algo_name, a, b, poly_range, black_list)
            a = []
            b = []

    # If there are any left over coefficients whos array was not evenly
    # divisible by the batch_size, queue them up also
    if len(a):
        if asynch:
            job = jobs.store.delay(db, precision, algo_name, a, b, poly_range, black_list)
            work.add(job) 
        else:
            jobs.store(db, precision, algo_name, a, b, poly_range, black_list)

    print('Done')
    return work


def wait(work):

    total_work = len(work)
    running = True

    while len(work):  # while there is still work to do ...

        utils.printProgressBar(total_work - len(work), total_work)

        completed_jobs = set()  # hold completed jobs done in this loop pass
        failed_jobs = set()     # same for failed jobs

        for job in work:
            
            if job.ready():
                completed_jobs.add(job)
                continue
            
        # print(f'completed:{len(completed_jobs)} failed:{len(failed_jobs)}')

        # Removes completed jobs from work
        work = work - completed_jobs - failed_jobs

        time.sleep(.1)
    
    utils.printProgressBar(total_work, total_work)
    return completed_jobs

