import os
import itertools
import time
from datetime import datetime
import logging
import mpmath
from mpmath import mpf, mpc
from redis import Redis, ConnectionPool
from rq import Queue
from rediscluster import RedisCluster

import algorithms
import config
import jobs
import postproc
import utils

log = logging.getLogger(__name__)

from data.wrapper import HashtableWrapper
work_queue_pool = ConnectionPool(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), db=os.getenv('WORK_QUEUE_DB'))


def run(max_precision=50, sync=False, silent=False):
    '''
    We want to:
        - make a first pass and find all key matches between the two sides
        - with all matches, 
    '''
    log.info(f'[search.run] max_precision:{max_precision} sync:{sync} silent:{silent} at {time.time()}')

    global work_queue_pool

    local_redis = Redis(connection_pool=work_queue_pool, db=os.getenv('WORK_QUEUE_DB'))
    q = Queue(connection=local_redis)
    log.debug(f'Localhost redis work queue is {os.getenv("WORK_QUEUE_DB")}')


    lhs_db = HashtableWrapper('lhs')
    rhs_db = HashtableWrapper('rhs')

    count = 0
    dbsize = lhs_db.size()

    for lhs_keys in lhs_db.scan():

        if sync:
            queue_search(lhs_keys, sync)
        else:
            q.enqueue(queue_search, lhs_keys, sync)
        
        count += 1
        if not silent:
            utils.printProgressBar(count, dbsize, f'Searching {count}/{dbsize}')

    jobs.wait(0, 0, silent)

    match_db = HashtableWrapper('match')
    print(f'Found {match_db.size()} matches')

    print()

def queue_search(lhs_keys, sync):
    global work_queue_pool

    local_redis = Redis(connection_pool=work_queue_pool, db=os.getenv('WORK_QUEUE_DB'))
    q = Queue(connection=local_redis)

    rhs_db = HashtableWrapper('rhs')

    print(f'lhs_key count:{len(lhs_keys)}')

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

    print(f'lhs_key {lhs_key} rhs_key count:{len(rhs_keys)}')

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
        _,_,lhs_postproc_id,lhs_result,_,_,_ = eval(lhs_val)
        _,_,rhs_postproc_id,rhs_result,_,_,_ = eval(rhs_val)

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
                match_db.set(key_value, (eval(lhs_val), eval(rhs_val)) )
            elif lhs_postproc_id != rhs_postproc_id:
                # if both sides are not using the same postproc, also add it
                match_db.set(key_value, (eval(lhs_val), eval(rhs_val)) )
        else:
            pass
            # They don't match when we have only added the fractional part
            # '0.33333333333'  != '3.33333333333'


# def test():

#     log.debug(f'Waiting for remaining {len(work)} items to finish...')
#     jobs.wait(0, 0, silent)
#     for job in work:
#         if job.result:
#             matches |= job.result

#     # update redis with our search progress so we can pick up where we left off

#     if not silent:
#         utils.printProgressBar(100, 100)

#     log.info(f'Found {len(matches)} initial matches')

    # # 'matches()' contains the arguments where the values matched exactly
    # # at 15 decimal places (whatever is in the config)
    # #
    # # Now lets try matching more decimal places
    # bigger_matches = set()

    # redis_conn = Redis(host=os.getenv('REDIS_HOST') , db=os.getenv('WORK_QUEUE_DB'))
    # q = Queue(connection=redis_conn)

    # # Loop over and over, doubling the decimal precision until decimal places 
    # # exceeds 100 or until there are no more matches
    # while len(matches) and mpmath.mp.dps < max_precision:
    #     bigger_matches = set()

    #     mpmath.mp.dps *= 2  # increase the decimal precision

    #     # cap it if it exceeds the maximum requested
    #     if mpmath.mp.dps > max_precision:
    #         mpmath.mp.dps = max_precision

    #     count = 0 # for progress bar

    #     work = set()

    #     for lhs_val, rhs_val in matches:
            
    #         # # Since we want more precision, also expand the polynomial range 10x
    #         # # for the continued fraction (or whatever algorithm it used)
    #         # # for the right hand side
    #         lhs_val = eval(lhs_val)
    #         rhs_val = list(eval(rhs_val))
    #         poly_range = eval(rhs_val[3]) # unpack the range
    #         poly_range = (poly_range[0] * -10, poly_range[1] * 10) # expand it
    #         rhs_val[3] = bytes(repr(poly_range), 'utf-8') # re-pack the range

    #         # # solve both sides with the new precision
    #         # lhs = mpmath.fabs(jobs.reverse_solve(eval(lhs_val)))
    #         # rhs = mpmath.fabs(jobs.reverse_solve(rhs_algo))

    #         if debug:
    #             result = jobs.check_match(mpmath.mp.dps, repr(lhs_val), repr(rhs_val))
    #             if result:
    #                 bigger_matches.add( result )
    #         else:

    #             job = q.enqueue(jobs.check_match, mpmath.mp.dps, repr(lhs_val), repr(rhs_val))
    #             work.add(job)

    #         if not silent:
    #             count += 1
    #             utils.printProgressBar(count, len(matches), prefix=f' Queueing {mpmath.mp.dps} places')


    #     # Wait for the set of jobs
    #     results = jobs.wait(work, silent)

    #     for result in results:
    #         if result is not None:
    #             bigger_matches.add( (result[0], result[1]) )
            
    #     if not silent:
    #         print()
    #         print(f'Found {len(bigger_matches)} matches at {mpmath.mp.dps} decimal places ...')
        
    #     matches = bigger_matches

    # print(f'Saving matches.p  ... ')
    # pickle.dump( matches, open( "matches.p", "wb" ) )
    # dump_output("matches.p")

def generate_sequences(a_gen, b_gen):
    
    name, args = a_gen
    args = eval(args)
    a_seq = generate_sequence(name, *args)

    name, args = b_gen
    args = eval(args)
    b_seq = generate_sequence(name, *args)

    sequence_pairs = list(itertools.product(a_seq, b_seq))
    return sequence_pairs


def generate_sequence(name, *args):
    func = getattr(algorithms, name)
    seq = func(*args)

    return seq






