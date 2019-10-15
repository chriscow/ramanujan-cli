import os, time
import inspect
import itertools
import logging
from datetime import datetime, timedelta

from redis import Redis, ConnectionPool
from rq import Worker, Queue
from rq.worker import WorkerStatus

import algorithms
from data.wrapper import HashtableWrapper
import postproc
import utils
import config

import mpmath
from mpmath import mpf, mpc

log = logging.getLogger(__name__)

work_queue_pool = ConnectionPool(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), db=os.getenv('WORK_QUEUE_DB'))
redis_pool = ConnectionPool(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'))


def ping(timestamp):
    return timestamp


def store(side, accuracy, algo_name, args_list, sequence_index, a_gen, b_gen, black_list, run_postproc):
    '''
    This method is queued up by the master process to be executed by a Celery worker.

    It calls the given algorithm with the given arguments and stores the value and
    arguments to arrive at that value in Redis.  Then, if configured, it runs the
    result through all the postproc.py functions to alter the result and stores
    all those too.

    Arguments

    args_list - list of a and b sequences. We pass each pair of sequences into the algorithm
    sequence_index - the STARTING index of the generated sequence. If you want to reproduce the sequence
        you have to generate all sequences, do an itertools.product() then index that list using sequence_index
    '''

    db = HashtableWrapper(side)

    # Get the actual function from the name passed in
    algo = getattr(algorithms, algo_name)

    # Get all the functions in the postproc module
    funcs = [fn for name,fn in inspect.getmembers(postproc) if inspect.isfunction(fn)]

    # These are just to track times for various blocks of code
    start = datetime.now()
    algo_times = []
    post_times = []
    redis_times = []

    for args in args_list:

        # utils.info(log, f'Starting {algo.__name__} at {datetime.now() - start}')

        # Call the algorithm function
        st = datetime.now()

        if hasattr(algo, 'validate'):
            if not algo.validate(*args):
                continue

        value = algo(*args)
        if value in black_list:
            continue

        algo_times.append( (datetime.now() - st).total_seconds() )

        # utils.info(log, f'{algo.__name__} value:{value}')

        # Loop through all the postproc functions defined in postproc.py
        for fn in funcs:
            
            # utils.info(log, f'[{datetime.now() - start}] fn:{fn.__name__} value:{value}')

            # run the algo value through the postproc function
            st = datetime.now()

            # If we are configued to run the postproc functions, do so
            # otherwise, just use the value from above and identify
            # the postproc function as identity() type_id == 0
            if run_postproc:
                result = fn(value) # run the postproc function against the value
            else:
                fn.type_id = 0 # identity function
                result = value

            # utils.info(log, f'post:{fn.__name__} value:{result}')

            post_times.append( (datetime.now() - st).total_seconds() )
            
            if mpmath.isnan(result) or mpmath.isinf(result):
                continue


            algo_data = (side, algo.type_id, fn.type_id, result, args, sequence_index, a_gen, b_gen)


            # verify = reverse_solve(algo_data)
            # assert(verify == result)

            # Convert 'result' to a set containing what numbers we will use for keys
            if isinstance(result, mpc):
                # If complex, send the real part, imaginary part, 
                # and the fractional parts of each
                keys = set([mpmath.frac(result.real), mpmath.frac(result.imag)])
            else:
                # If real, just send itself and the fractional part
                keys = set([mpmath.frac(result)])


            # remove any values contained in the blacklist
            keys = keys - black_list

            # finally, send the keys and values to redis
            for key in keys:
                redis_start = datetime.now()
                # utils.info(log, f'setting key {key}')
                db.set(key, algo_data)
                redis_times.append( (datetime.now() - redis_start).total_seconds() )

            # bail out early if we are not running the post-proc functions
            if not run_postproc:
                break
        
        sequence_index += 1
            

        # utils.debug(log, f'Algo+Post for {algo.__name__} {a_coeff} {b_coeff} done at {datetime.now() - start}')
    
    commit_start = datetime.now()
    db.commit()
    commit_time = (datetime.now() - commit_start).total_seconds()

    elapsed = (datetime.now() - start).total_seconds()

    if len(redis_times):
        utils.info(log, f'elapsed:{elapsed} algo: {sum(algo_times)} post: {sum(post_times)} redis: {sum(redis_times)} len(redis): {len(redis_times)} avg(redis): {sum(redis_times) / len(redis_times)} commit: {commit_time}')
    # return test


def wait(min, max, silent):
    '''
    Waits on a set of celery job objects to complete. The caller is responsible
    for calling forget() on the result to remove it from the backend.

    Arguments:
        work - a Python set() object containing Celery AsyncResult instances

    Returns:
        All of the jobs passed in
    '''
    global work_queue_pool

    redis_conn = Redis(connection_pool=work_queue_pool)
    default_queue = Queue(connection=redis_conn)
    workers = Worker.all(connection=redis_conn)
    worker_count = len(workers)

    total_work = default_queue.count
    eta = timedelta()

    min *= worker_count
    max *= worker_count

    if total_work < max:
        return

    sleep_time = 0

    while default_queue.count > min:

        # utils.debug(log, f'[jobs.wait] Waiting for {total_work} jobs to complete')

        # Wait a little bit before checking if more work has completed
        time.sleep(1)

        if 0 == worker_count:
            utils.warn(log, 'There are no workers')

        if not silent:
            utils.printProgressBar(total_work - default_queue.count + min, total_work - min, prefix=f'Waiting {total_work - default_queue.count + min} / {total_work - min}') 

    if max == 0:

# WorkerStatus = enum(
#     'WorkerStatus',
#     STARTED='started',
#     SUSPENDED='suspended',
#     BUSY='busy',
#     IDLE='idle'
# )
        idle_workers = 0

        while idle_workers != len(workers):
            
            idle_workers = 0

            # keep our workers list up to date
            workers = Worker.all(connection=redis_conn)

            # wait for all workers to finish
            for worker in workers:
                if worker.get_state() == WorkerStatus.IDLE:
                    idle_workers += 1

            if idle_workers < len(workers):
                time.sleep(1)        

def queue_search(lhs_keys, sync):

    local_redis = Redis(db=os.getenv('WORK_QUEUE_DB'))
    q = Queue(connection=local_redis)

    rhs_db = HashtableWrapper('rhs')

    # key_matches() enumerates all the keys in the hashtable from the left hand side,
    # and finds a match on the right hand side.  
    for lhs_key in lhs_keys:

        _, key_value, _ = str(lhs_key).split(':')

        for rhs_keys in rhs_db.scan(key_value):
            
            if rhs_keys:
                if sync:
                    find_matches(lhs_key, rhs_keys)
                else:
                    q.enqueue(find_matches, lhs_key, rhs_keys)
            

def find_matches(lhs_key, rhs_keys):
    
    lhs_db = HashtableWrapper('lhs')
    rhs_db = HashtableWrapper('rhs')
    match_db = HashtableWrapper('match')

    lhs_val = lhs_db.redis.get(lhs_key)
    _, key_value, _ = str(lhs_key).split(':')

    for rhs_key in rhs_keys:  
        
        rhs_val = rhs_db.redis.get(rhs_key)

        if rhs_val is None:
            continue

        # Expand the algorithm arguments etc from the data in the hashtable
        # Underscore just means we are ignoring that entry
        # The format of these values is:
        #   - algorithm type_id from algorithms.py that generated the result
        #   - postproc type_id of the function from postprocs.py that altered the result
        #   - final calculated value
        #   - algorithm arguments
        #   - a_generator method and args
        #   - b generator method and args

        # algo.type_id, fn.type_id, result, repr(args), a_gen, b_gen
        _,_,lhs_postproc_id,lhs_result,_,_,_,_ = eval(lhs_val)
        _,_,rhs_postproc_id,rhs_result,_,_,_,_ = eval(rhs_val)

        # Check the absolute value of both sides and make sure they are the same
        # if mpmath.fabs(lhs_result)[:8] == mpmath.fabs(rhs_result):
        #     matches.add((lhs_val, rhs_val))

        # matching only the fractional part
        lhs_result = mpmath.frac(mpmath.fabs(lhs_result))
        rhs_result = mpmath.frac(mpmath.fabs(rhs_result))

        if str(lhs_result)[:mpmath.mp.dps - 2] == str(rhs_result)[:mpmath.mp.dps - 2]:
            # if both sides are just using the identity() post proc (noop)
            # then add it to the matches.
            if lhs_postproc_id == 0 and rhs_postproc_id == 0:
                match_db.set(key_value, (lhs_val, rhs_val) )
            elif lhs_postproc_id != rhs_postproc_id:
                # if both sides are not using the same postproc, also add it
                match_db.set(key_value, (lhs_val, rhs_val) )
        else:
            pass
            # They don't match when we have only added the fractional part
            # '0.33333333333'  != '3.33333333333'
    
def reverse_solve(side, algo_data):
    '''
    Takes the data we are going to store and solves it to 
    verify we get the result back
    '''
    ht = HashtableWrapper(side)

    if isinstance(algo_data, str) or isinstance(algo_data, bytes):
        raise Exception('You forgot to unpack algo_data')

    algo_id, postfn_id, result, serialized_range, a_coeff, b_coeff = algo_data

    algos = utils.get_funcs(algorithms)
    postprocs = utils.get_funcs(postproc)

    algo = algos[algo_id]
    post = postprocs[postfn_id]

    try:
        # if it can be cast to a float, then convert it to mpf
        float(serialized_range)
        poly_range = mpf(serialized_range)
    except ValueError:
        poly_range = eval(serialized_range)


    value = algorithms.solve(a_coeff, b_coeff, poly_range, algo)
    value = post(value)

    return value



def check_match(dps, lhs_val, rhs_val):
    '''
    Takes the arguments from the left and right hand sides and reverse-solves
    them to get values.

    Then it compares the values for equivilency based on the current mpmath
    decimal accuracy, minus two places (try to handle rounding ... not perfect)

    Returns
        If the two sides are 'equivilent', it returns them both.  Otherwise,
        the function returns None.
    '''
    mpmath.mp.dps = dps

    # solve both sides with the new precision
    lhs = mpmath.fabs(reverse_solve(eval(lhs_val)))
    rhs = mpmath.fabs(reverse_solve(eval(rhs_val)))

    # if there is a match, save it
    if str(lhs)[:mpmath.mp.dps - 2] == str(rhs)[:mpmath.mp.dps - 2]:
        return (lhs_val, rhs_val)
    else:
        return None



if __name__ == '__main__':

    import main
    main.check_environment()

    db = 14 # unused database
    precision = 8
    black_list = set([])


    #zero
    store(db, precision, 'continued_fraction', [(0,0,0)], [(0,0,0)], '(0,200)', black_list, True)

    # phi
    store(db, precision, 'continued_fraction',[(1,0,0)], [(1,0,0)], '(0,200)', black_list, True)

    a = []
    b = []
    a_range = [[ [1,4], [0,2], [0,1] ]]
    b_range = [[ [0,2], [-1,1], [0,1] ]]
    for a_coeff, b_coeff in algorithms.iterate_coeff_ranges(a_range, b_range):
        a.append(a_coeff)
        b.append(b_coeff)

    store(db, precision, 'continued_fraction', a, b, '(0,200)', black_list, False)

    store(db, precision, 'rational_function', [(0,1,0)], [(1,0,0)], mpmath.e, black_list, False)

    utils.info(log, 'jobs.py passed')
