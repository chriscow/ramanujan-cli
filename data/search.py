import os
import itertools
import mpmath
from mpmath import mpf
from redis import Redis
from rq import Queue

import algorithms
import config
import jobs
import postproc
import utils

from data.wrapper import HashtableWrapper

def run(max_precision=50, debug=False, silent=False):
    '''
    We want to:
        - make a first pass and find all key matches between the two sides
        - with all matches, 
    '''
    lhs_db = HashtableWrapper(os.getenv('LHS_DB'), config.hash_precision)
    rhs_db = HashtableWrapper(os.getenv('RHS_DB'), config.hash_precision)

    lhs_size = lhs_db.redis.dbsize()
    rhs_size = rhs_db.redis.dbsize()

    index = 0
    spinner = '|/-\\'


    postprocs = utils.get_funcs(postproc)
    algos = utils.get_funcs(algorithms)
    matches = set()

    cur = 0

    # key_matches() enumerates all the keys in the hashtable from the left hand side,
    # and finds a match on the right hand side.  
    for key, lhs_vals, rhs_vals in key_matches(lhs_db, rhs_db, silent):

        # These are just for the progress bar
        cur += 1
        cur_sub = 0

        # How many combinations are there we need to check? (for progress bar)
        subtotal = len(lhs_vals) * len(rhs_vals)

        # Enumerates all possible combinations of left and right
        for lhs_val, rhs_val in itertools.product(lhs_vals, rhs_vals):  

            # Expand the algorithm arguments etc from the data in the hashtable
            # Underscore just means we are ignoring that entry
            # The format of these values is:
            #   - algorithm type_id from algorithms.py that generated the result
            #   - postproc type_id of the function from postprocs.py that altered the result
            #   - final calculated value
            #   - polynomial range or constant value (depends on left or right side)
            #   - a coefficients
            #   - b coefficients
            _,_,lhs_result,_,_,_ = eval(lhs_val)
            _,_,rhs_result,_,_,_ = eval(rhs_val)

            # Check the absolute value of both sides and make sure they are the same
            # if mpmath.fabs(lhs_result)[:8] == mpmath.fabs(rhs_result):
            #     matches.add((lhs_val, rhs_val))
            lhs_result = mpmath.fabs(lhs_result)
            rhs_result = mpmath.fabs(rhs_result)

            if str(lhs_result)[:mpmath.mp.dps - 2] == str(rhs_result)[:mpmath.mp.dps - 2]:
                matches.add( (lhs_val, rhs_val) )
            else:
                pass
                # They don't match when we have only added the fractional part
                # '0.33333333333'  != '3.33333333333'
                
            if not silent:
                index += 1
                cur_sub += 1
                utils.printProgressBar(cur, lhs_size, prefix=f'{spinner[index % len(spinner)]} {key}', suffix=f'{cur_sub}/{subtotal} {cur}/{lhs_size}      ')


    if not silent:
        utils.printProgressBar(lhs_size, lhs_size, suffix=f'                          ')
        print()
        print(f'Found {len(matches)} matches at {mpmath.mp.dps} decimal places')


    # 'matches()' contains the arguments where the values matched exactly
    # at 15 decimal places (whatever is in the config)
    #
    # Now lets try matching more decimal places
    bigger_matches = set()

    redis_conn = Redis(host=os.getenv('REDIS_HOST') , db=os.getenv('WORK_QUEUE_DB'))
    q = Queue(connection=redis_conn)

    # Loop over and over, doubling the decimal precision until decimal places 
    # exceeds 100 or until there are no more matches
    while len(matches) and mpmath.mp.dps < max_precision:
        bigger_matches = set()

        mpmath.mp.dps *= 2  # increase the decimal precision

        # cap it if it exceeds the maximum requested
        if mpmath.mp.dps > max_precision:
            mpmath.mp.dps = max_precision

        count = 0 # for progress bar

        work = set()

        for lhs_val, rhs_val in matches:
            
            # # Since we want more precision, also expand the polynomial range 10x
            # # for the continued fraction (or whatever algorithm it used)
            # # for the right hand side
            lhs_val = eval(lhs_val)
            rhs_val = list(eval(rhs_val))
            poly_range = eval(rhs_val[3]) # unpack the range
            poly_range = (poly_range[0] * -10, poly_range[1] * 10) # expand it
            rhs_val[3] = bytes(repr(poly_range), 'utf-8') # re-pack the range

            # # solve both sides with the new precision
            # lhs = mpmath.fabs(jobs.reverse_solve(eval(lhs_val)))
            # rhs = mpmath.fabs(jobs.reverse_solve(rhs_algo))

            if debug:
                result = jobs.check_match(mpmath.mp.dps, repr(lhs_val), repr(rhs_val))
                if result:
                    bigger_matches.add( result )
            else:

                job = q.enqueue(jobs.check_match, mpmath.mp.dps, repr(lhs_val), repr(rhs_val))
                work.add(job)

            if not silent:
                count += 1
                utils.printProgressBar(count, len(matches), prefix=f' Queueing {mpmath.mp.dps} places', suffix='     ')


        # Wait for the set of jobs
        results = jobs.wait(work, silent)

        for result in results:
            if result is not None:
                bigger_matches.add( (result[0], result[1]) )
            
        if not silent:
            print()
            print(f'Found {len(bigger_matches)} matches at {mpmath.mp.dps} decimal places ...')
        
        matches = bigger_matches
    
    # By the time we reach here, if there were any high-precision matches, 
    # dump out the data to the screen
    mpmath.mp.dps = 15 # back to default
    for lhs, rhs in bigger_matches:
        lhs_algo_id, lhs_post, lhs_result, const, lhs_a_coeff, lhs_b_coeff = eval(lhs)
        rhs_algo_id, rhs_post, rhs_result, poly_range, rhs_a_coeff, rhs_b_coeff = eval(rhs)

        print('')
        print('-' * 60)
        print('')

        #
        # output the fancy version for known functions
        #
        if lhs_algo_id == 2: # rational_function
            numerator = utils.polynomial_to_string(lhs_a_coeff, eval(const))
            denominator = utils.polynomial_to_string(lhs_b_coeff, eval(const))
            post = postprocs[rhs_post].__name__ + '(x) <== '
            if rhs_post == 0: #identity
                post = ''

            if denominator != '1':
                print(f'LHS: {post} {numerator} / {denominator}')
            else:
                print(f'LHS: {post} {numerator}')
        else:
            print(f'LHS: const:{const} {postprocs[lhs_post].__name__}( {algos[lhs_algo_id].__name__} (a:{lhs_a_coeff} b:{lhs_b_coeff}))')

        if rhs_algo_id == 1: # continued fraction
            cont_frac = utils.cont_frac_to_string(rhs_a_coeff, rhs_b_coeff)
            post = postprocs[rhs_post].__name__ + '(x) <== '
            if rhs_post == 0: #identity
                post = ''

            print(f'RHS: {post} {cont_frac}')
        else:
            print(f'RHS: {rhs_result} {postprocs[rhs_post].__name__}( {algos[rhs_algo_id].__name__} (a:{rhs_a_coeff} b:{rhs_b_coeff})) for x => poly range:{poly_range}')
        print('')
    


    

def key_matches(lhs, rhs, silent):
    '''
    Searches for keys from the lhs in the rhs.

    Returns:
        Three element array:
            matching key, lhs algo arguments, rhs algo arguments
    '''
    for key in lhs.redis.scan_iter():

        # *hs_vals is a list of algorithm parameters used to generate the result
        lhs_vals = lhs.get(key)
        rhs_vals = rhs.get(key)
        if rhs_vals:
            yield (key, lhs_vals, rhs_vals)