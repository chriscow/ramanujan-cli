import os
import time
import itertools
import logging
import hashlib

import mpmath
from mpmath import mpf, mpc

from redis import Redis, ConnectionPool
from rq import Queue
from rq.worker import Worker

import algorithms
import config
import jobs
import utils

import dotenv
dotenv.load_dotenv()

log = logging.getLogger(__name__)

work_queue_pool = ConnectionPool(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), db=os.getenv('WORK_QUEUE_DB'))



def run(side, db, use_constants, sync=False, silent=False):
    '''
    This function does the actual work of queueing the jobs to Celery for
    processing in other processes or machines
    '''
    precision  = config.hash_precision
    const_type = type(mpmath.e)

    a_sequences = side["a_sequences"]
    b_sequences = side["b_sequences"]

    black_list = side["black_list"]
    run_postproc = side["run_postproc"]

    redis_conn = Redis(connection_pool=work_queue_pool)
    worker_count = len(Worker.all(connection=redis_conn))

    utils.info(log, f'''

    db: {db}
    use_constants: {use_constants}
    sync: {sync}
    hash precision: {config.hash_precision}
    algorithm: {','.join([algo.__name__ for algo in side["algorithms"]])}
    run post proc f(x)?: {side["run_postproc"]}
    worker count: {worker_count}
    
    ''')
        
    for algo in side["algorithms"]:
        for a_sequence, b_sequence in itertools.product(a_sequences, b_sequences):
            
            a_gen  = a_sequence["generator"]
            a_args = a_sequence["arguments"]
            b_gen  = b_sequence["generator"]
            b_args = b_sequence["arguments"]

            if use_constants:
                count = 0

                # Loop through the list of constants in the config file.  The constant
                # value is used for the 'polynomial range' as a single value
                for const in config.constants:
                    
                    # Determine if we are using a constant mpmath value or a decimal
                    try:
                        # if it can be cast to a float, then convert it to mpf
                        float(const)
                        const = mpf(const)
                    except ValueError:
                        # we have a constant like 'mpmath.phi'
                        const = mpf(eval(const))

                    # Total hack  :(
                    a_args[1] = const
                    b_args[1] = const
                    
                    work = set()

                    # queue_work generates several jobs based on the a and b ranges
                    for jobs in _queue_work(db, precision, algo.__name__, 
                            a_gen, a_args, 
                            b_gen, b_args, 
                            black_list, run_postproc, 
                            sync=sync, silent=True):
                        
                        work |= jobs

                    count += 1

                    if not silent:
                        utils.printProgressBar(count, len(config.constants) + 1, prefix='Queuing constants', suffix='     ')
                
                yield work
                
            else:
                for jobs in _queue_work(db, precision, algo.__name__, 
                    a_gen, a_args, 
                    b_gen, b_args, 
                    black_list, run_postproc, 
                    sync=sync, silent=silent):

                    yield jobs


def _queue_work(db, precision, algo_name, a_generator, a_gen_args, b_generator, b_gen_args, black_list, run_postproc, sync=False, silent=False):
    '''
    Calls the generator for the a-sequence and b-sequence, then
    queues the algorithm calculations to be run and stored in the database.
    '''
    # Each job will contain this many a/b coefficient pairs
    batch_size = config.batch_size if not run_postproc else 10

    arg_list = []  # holds a subset of the coefficient a-range
    work = set()  # set of all jobs queued up to know when we are done

    gen_data = repr( (a_generator, a_gen_args, b_generator, b_gen_args) )

    # Generate the sequences
    a_seq = a_generator(*a_gen_args)
    b_seq = b_generator(*b_gen_args)

    # Serialize

    # for the progress bar
    sequence_pairs = list(itertools.product(a_seq, b_seq))
    total_work = len(sequence_pairs)
    count = 1
    index = 0
    spinner = '|/-\\'

    redis_conn = Redis(connection_pool=work_queue_pool)
    worker_count = len(Worker.all(connection=redis_conn))

    sequence_index = 0
    for args in sequence_pairs:

        if len(work) > config.max_workqueue_size: # * worker_count:  # scaled to how many workers are registered and working
            yield work
            work.clear()

        arg_list.append(args)
        count += 1

        # When the list of a's and b's are up to batch_size, queue a job
        if count % batch_size == 0:
            # We are queuing arrays of coefficients to work on
            if sync:
                # if we are debugging, don't process this job in a separate program
                # (keeps it synchronous and all in the same process for debugging)
                jobs.store(db, precision, algo_name, arg_list, 
                    sequence_index,
                    (a_generator.__name__, repr(a_gen_args)),
                    (b_generator.__name__, repr(b_gen_args)),
                    black_list, run_postproc)
            else:
                # adding .delay after the function name queues it up to be 
                # executed by a Celery worker in another process / machine 
                job = enqueue(db, precision, algo_name, arg_list, 
                        sequence_index,
                        (a_generator.__name__, repr(a_gen_args)),
                        (b_generator.__name__, repr(b_gen_args)),
                        black_list, run_postproc)
                
                work.add(job)   # hold onto the job info

            arg_list = []
        
        sequence_index += 1

        if not silent:
            index += 1
            utils.printProgressBar(count, total_work, prefix=f'{spinner[index % len(spinner)]} Queueing {count + 1}/{total_work}', suffix='     ')

    # If there are any left over coefficients whos array was not evenly
    # divisible by the batch_size at the end, queue them up also
    if len(arg_list):
        if sync:
            jobs.store(db, precision, algo_name, arg_list, 
                sequence_index,
                (a_generator.__name__, repr(a_gen_args)),
                (b_generator.__name__, repr(b_gen_args)),
                black_list, run_postproc)
        else:
            job = enqueue(db, precision, algo_name, arg_list,
                    sequence_index,
                    (a_generator.__name__, repr(a_gen_args)),
                    (b_generator.__name__, repr(b_gen_args)),
                    black_list, run_postproc)
               
            work.add(job) 

    yield work

def enqueue(*argv):
    global work_queue_pool
    redis_conn = Redis(connection_pool=work_queue_pool)
    q = Queue(connection=redis_conn)
    
    retry_time = 1  # seconds

    while retry_time < 600:
        try:
            job = q.enqueue(jobs.store, result_ttl=config.job_result_ttl, *argv)
            return job
        except Exception as err:
            utils.warn(log, err)
            utils.warn(log, f'Retrying enqueue in {retry_time} seconds...')
            time.sleep(retry_time)
            retry_time *= 5

    raise Exception('Redis server seems to have died. Cannot enqueue.')
    




if __name__ == '__main__':

    pass

