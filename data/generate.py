import os

import mpmath
from mpmath import mpf

from redis import Redis
from rq import Queue

import algorithms
import config
import jobs
import utils

def run(side, db, use_constants, debug=False, silent=False):
    '''
    This function does the actual work of queueing the jobs to Celery for
    processing in other processes or machines
    '''
    precision  = config.hash_precision
    const_type = type(mpmath.e)

    algo   = side.algorithm.__name__

    a_range    = side.a_range
    b_range    = side.b_range
    poly_range = config.polynomial_range
    black_list = side.black_list
    run_postproc = side.run_postproc
    
    work = set()

    if use_constants:
        count = 0

        # Loop through the list of constants in the config file.  The constant
        # value is used for the 'polynomial range' as a single value
        for const in config.constants:

            # queue_work generates several jobs based on the a and b ranges
            jobs = _queue_work(db, precision, algo, a_range, b_range, const, black_list, run_postproc, debug=debug, silent=True)
            work |= jobs
            count += 1

            if not silent:
                utils.printProgressBar(count, len(config.constants) + 1, prefix='Queuing constants', suffix='     ')
    else:
        work = _queue_work(db, precision, algo, a_range, b_range, repr(config.polynomial_range), black_list, run_postproc, debug=debug, silent=silent)

    return work


def _queue_work(db, precision, algo_name, a_range, b_range, poly_range, black_list, run_postproc, debug=False, silent=False):
    '''
    Queues the algorithm calculations to be run and stored in the database.
    '''

    # Each job will contain this many a/b coefficient pairs
    batch_size = 100

    # for the progress bar
    total_work = algorithms.range_length(b_range, algorithms.range_length(a_range))
    count = 1

    a = []  # holds a subset of the coefficient a-range
    b = []  # holds a subset of the coefficient b-range
    work = set()  # set of all jobs queued up to know when we are done

    redis_conn = Redis(host=os.getenv('REDIS_HOST') , db=os.getenv('WORK_QUEUE_DB'))
    q = Queue(connection=redis_conn)

    # Loop through all coefficient possibilities
    for a_coeff, b_coeff in algorithms.iterate_coeff_ranges(a_range, b_range):

        a.append(a_coeff)
        b.append(b_coeff)
        count += 1

        # When the list of a's and b's are up to batch_size, queue a job
        if count % batch_size == 0:
            # We are queuing arrays of coefficients to work on
            if debug:
                # if we are debugging, don't process this job in a separate program
                # (keeps it synchronous and all in the same process for debugging)
                jobs.store(db, precision, algo_name, a, b, poly_range, black_list, run_postproc)
            else:
                # adding .delay after the function name queues it up to be 
                # executed by a Celery worker in another process / machine            
                job = q.enqueue(jobs.store, db, precision, algo_name, a, b, poly_range, black_list, run_postproc)
                
                work.add(job)   # hold onto the job info

            if not silent:
                utils.printProgressBar(count, total_work, prefix=f'Queueing {count}/{total_work}', suffix='     ')

            a = []
            b = []

    # If there are any left over coefficients whos array was not evenly
    # divisible by the batch_size at the end, queue them up also
    if len(a):
        if debug:
            jobs.store(db, precision, algo_name, a, b, poly_range, black_list, run_postproc)
        else:
            job = q.enqueue(jobs.store, db, precision, algo_name, a, b, poly_range, black_list, run_postproc)
               
            work.add(job) 

    return work


if __name__ == '__main__':

    pass