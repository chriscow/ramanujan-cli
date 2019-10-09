import os
import time
import itertools

import mpmath
from mpmath import mpf, mpc

from redis import Redis, ConnectionPool
from rq import Queue

import algorithms
import config
import jobs
import utils

import dotenv
dotenv.load_dotenv()

work_queue_pool = ConnectionPool(host=os.getenv('REDIS_HOST'), port=6379, db=os.getenv('WORK_QUEUE_DB'))

def run(side, db, use_constants, debug=False, silent=False):
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

    print(f'''

    hash precision: {config.hash_precision}
    algorithm: {','.join([algo.__name__ for algo in side["algorithms"]])}
    run post proc f(x)?: {side["run_postproc"]}
    
    ''')
    
    work = set()

    for algo in side["algorithms"]:
        for a_sequence, b_sequence in itertools.product(a_sequences, b_sequences):

            if len(work) > 10000:
                yield work
                work.clear()
            
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

                    # queue_work generates several jobs based on the a and b ranges
                    work |= _queue_work(db, precision, algo.__name__, 
                        a_gen, a_args, 
                        b_gen, b_args, 
                        black_list, run_postproc, 
                        debug=debug, silent=True)
                    count += 1

                    if not silent:
                        utils.printProgressBar(count, len(config.constants) + 1, prefix='Queuing constants', suffix='     ')
            else:
                work |= _queue_work(db, precision, algo.__name__, 
                    a_gen, a_args, 
                    b_gen, b_args, 
                    black_list, run_postproc, 
                    debug=debug, silent=silent)

    return work


def _queue_work(db, precision, algo_name, a_generator, a_gen_args, b_generator, b_gen_args, black_list, run_postproc, debug=False, silent=False):
    '''
    Calls the generator for the a-sequence and b-sequence, then
    queues the algorithm calculations to be run and stored in the database.
    '''

    # Each job will contain this many a/b coefficient pairs
    batch_size = 100

    arg_list = []  # holds a subset of the coefficient a-range
    work = set()  # set of all jobs queued up to know when we are done

    gen_data = repr( (a_generator, a_gen_args, b_generator, b_gen_args) )

    # Generate the sequences
    a_seq = a_generator(*a_gen_args)
    b_seq = b_generator(*b_gen_args)

    # Serialize

    # for the progress bar
    all_args = list(itertools.product(a_seq, b_seq))
    total_work = len(all_args)
    count = 1

    for args in all_args:

        arg_list.append(args)
        count += 1

        # When the list of a's and b's are up to batch_size, queue a job
        if count % batch_size == 0:
            # We are queuing arrays of coefficients to work on
            if debug:
                # if we are debugging, don't process this job in a separate program
                # (keeps it synchronous and all in the same process for debugging)
                jobs.store(db, precision, algo_name, arg_list, 
                    (a_generator.__name__, repr(a_gen_args)),
                    (b_generator.__name__, repr(b_gen_args)),
                    black_list, run_postproc)
            else:
                # adding .delay after the function name queues it up to be 
                # executed by a Celery worker in another process / machine 
                job = enqueue(db, precision, algo_name, arg_list, 
                        (a_generator.__name__, repr(a_gen_args)),
                        (b_generator.__name__, repr(b_gen_args)),
                        black_list, run_postproc)
                
                work.add(job)   # hold onto the job info

            if not silent:
                utils.printProgressBar(count, total_work, prefix=f'Queueing {count}/{total_work}', suffix='     ')

            arg_list = []

    # If there are any left over coefficients whos array was not evenly
    # divisible by the batch_size at the end, queue them up also
    if len(arg_list):
        if debug:
            jobs.store(db, precision, algo_name, arg_list, 
                (a_generator.__name__, repr(a_gen_args)),
                (b_generator.__name__, repr(b_gen_args)),
                black_list, run_postproc)
        else:
            job = enqueue(db, precision, algo_name, arg_list,
                    (a_generator.__name__, repr(a_gen_args)),
                    (b_generator.__name__, repr(b_gen_args)),
                    black_list, run_postproc)
               
            work.add(job) 

    return work

def enqueue(*argv):
    global work_queue_pool
    redis_conn = Redis(connection_pool=work_queue_pool)
    q = Queue(connection=redis_conn)
    
    retry_time = 1  # seconds

    while retry_time < 600:
        try:
            job = q.enqueue(jobs.store, *argv, result_ttl=86400)
            return job
        except Exception as err:
            print(err)
            print(f'Retrying enqueue in {retry_time} seconds...')
            time.sleep(retry_time)
            retry_time *= 5

    raise Exception('Redis server seems to have died. Cannot enqueue.')
    




if __name__ == '__main__':

    pass

