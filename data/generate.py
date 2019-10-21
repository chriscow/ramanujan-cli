import os
import time
import itertools
import logging
import hashlib
from datetime import datetime

import concurrent.futures

import mpmath
from mpmath import mpf, mpc

from redis import Redis, ConnectionPool
from rq import Queue
from rq.worker import Worker

import algorithms
import cache
import config
import jobs
import utils

import dotenv
dotenv.load_dotenv()

log = logging.getLogger(__name__)

work_queue_pool = ConnectionPool(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), db=os.getenv('WORK_QUEUE_DB'))
redis_pool = ConnectionPool(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'))


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

    global redis_pool

    print(f'''

    db: {db}
    use_constants: {use_constants}
    sync: {sync}
    hash precision: {config.hash_precision}
    algorithm: {','.join([algo.__name__ for algo in side["algorithms"]])}
    run post proc f(x)?: {run_postproc}
    worker count: {worker_count}
    
    ''')

    # Each job will contain this many a/b coefficient pairs
    # If we aren't running post proc functions, x10

    total_work = len(list(itertools.product(a_sequences, b_sequences))) * len(side["algorithms"])
    
    if use_constants:
        batch_size = 5 if run_postproc else 500
    else:
        batch_size = 20 if run_postproc else 100

    # If we are doing the constants, another 100x
    # batch_size = batch_size * 10 if use_constants else batch_size
    seq_cache = cache.SequenceCache(redis_pool)
    
    count = 0

    for algo in side["algorithms"]:
        count += 1
        for a_sequence, b_sequence in itertools.product(a_sequences, b_sequences):
            count += 1
            if not silent:
                utils.printProgressBar(count, total_work, prefix=f'Generating {count}/{total_work}')

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

                    # Total hack  :( Set the second param to just the constant
                    a_args[1] = [const]
                    b_args[1] = [const]
                    
                    a_hash = seq_cache.generate(a_gen, a_args)
                    b_hash = seq_cache.generate(b_gen, b_args)

                    # queue_work generates several jobs based on the a and b ranges
                    _queue_work(db, precision, batch_size, algo.__name__, 
                            a_hash, 
                            b_hash, 
                            black_list, run_postproc, 
                            sync=sync, silent=silent, what=f'const:{utils.get_const_str(const)} ({count}/{total_work})')
                                        
            else:
                a_hash = seq_cache.generate(a_gen, a_args)
                b_hash = seq_cache.generate(b_gen, b_args)

                _queue_work(db, precision, batch_size, algo.__name__, 
                    a_hash, 
                    b_hash, 
                    black_list, run_postproc, 
                    sync=sync, silent=silent, what=f'{algo.__name__} ({count}/{total_work})')
        
            

    # wait for remaining work
    jobs.wait(0, 0, silent)
    


def _queue_work(db, precision, batch_size, algo_name, a_seq_hash, b_seq_hash, black_list, run_postproc, sync=False, silent=False, what=''):
    '''
    Calls the generator for the a-sequence and b-sequence, then
    queues the algorithm calculations to be run and stored in the database.
    '''

    global redis_pool
    what = what[:15]
    
    arg_list = []  # holds a subset of the coefficient a-range
    work = set()  # set of all jobs queued up to know when we are done

    # gen_data = repr( (a_generator, a_gen_args, b_generator, b_gen_args) )
    sequence_cache = cache.SequenceCache(redis_pool)

    # generate lists of sequences
    a_seq = sequence_cache.get(a_seq_hash)
    b_seq = sequence_cache.get(b_seq_hash)

    # Create pairs of sequences using every combination of each sequence
    sequence_pairs = list(itertools.product(a_seq, b_seq))

    # progress bar
    total_work = len(sequence_pairs) 
    count = 0
    index = 0
    spinner = '|/-\\'

    logging.debug(f'[_queue_work] {a_seq_hash} {b_seq_hash}')

    redis_conn = Redis(connection_pool=work_queue_pool)
    worker_count = len(Worker.all(connection=redis_conn))

    # all_args = [(db, precision, algo_name, pair, a_seq_hash, b_seq_hash, black_list, run_postproc)
    #     for pair in sequence_pairs]

    # with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    #     executor.map(jobs.store, all_args, chunksize=batch_size)


    for pairs in utils.chunks(sequence_pairs, batch_size):

        args = (db, precision, algo_name, pairs, a_seq_hash, b_seq_hash, black_list, run_postproc)

        # We are queuing arrays of coefficients to work on
        if sync:
            # if we are debugging, don't process this job in a separate program
            # (keeps it synchronous and all in the same process for debugging)
            jobs.store(*args)
        else:
            # adding .delay after the function name queues it up to be 
            # executed by a Celery worker in another process / machine 
            enqueue(*args)
            
            jobs.wait(config.min_workqueue_size, config.max_workqueue_size, silent)

        if not silent and count % 10 == 0:
            index += 1
            utils.printProgressBar(count, total_work, prefix=f'{spinner[index % len(spinner)]} Queueing {what} {count}/{total_work}')

        count += len(pairs)      

    # draw the final part
    if not silent and count % 10 == 0:
        index += 1
        utils.printProgressBar(count, total_work, prefix=f'{spinner[index % len(spinner)]} Queueing {what} {count}/{total_work}')

               
def enqueue(*argv):
    global work_queue_pool
    redis_conn = Redis(connection_pool=work_queue_pool)
    q = Queue(connection=redis_conn)
    
    retry_time = 1  # seconds

    while retry_time < 600:
        try:
            job = q.enqueue(jobs.store, result_ttl=0, *argv)
            return job
        except Exception as err:
            logging.warning(log, err)
            logging.warning(log, f'Retrying enqueue in {retry_time} seconds...')
            time.sleep(retry_time)
            retry_time *= 5

    raise Exception('Redis server seems to have died. Cannot enqueue.')
    




if __name__ == '__main__':

    pass

