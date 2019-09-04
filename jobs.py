import os
import inspect
import dotenv
import itertools
from datetime import datetime

import algorithms
import config
import data
import postproc
import utils

import mpmath
from mpmath import mpf

from celery import Celery
from celery.utils.log import get_task_logger

app = Celery()
app.config_from_object('celeryconfig')

dotenv.load_dotenv()

logger = get_task_logger(__name__)

@app.task()
def ping(timestamp):
    return timestamp

@app.task()
def store(db, accuracy, algo_name, a_coeffs, b_coeffs, serialized_range, black_list):
    '''
    This method is queued up by the master process to be executed by a Celery worker.

    It calls the given algorithm with the given arguments and stores the value and
    arguments to arrive at that value in Redis.  Then, if configured, it runs the
    result through all the postproc.py functions to alter the result and stores
    all those too.
    '''

    # The db number passed in indicated whether we are working on the left or right
    db = data.DecimalHashTable(db=db, accuracy=accuracy)

    # Get the actual function from the name passed in
    algo = getattr(algorithms, algo_name)

    # Creates a list of all combinations of coefficients
    coeff_list = zip(a_coeffs, b_coeffs)

    # Get all the functions in the postproc module
    funcs = [fn for name,fn in inspect.getmembers(postproc) if inspect.isfunction(fn)]

    # Determine if we are using a constant value or a range of values for x
    try:
        # if it can be cast to a float, then convert it to mpf
        float(serialized_range)
        poly_range = mpf(serialized_range)
    except ValueError:
        poly_range = eval(serialized_range)

    # These are just to track times for various blocks of code
    start = datetime.now()
    algo_times = []
    post_times = []
    redis_times = []


    for a_coeff, b_coeff in coeff_list:

        # logger.debug(f'Starting {algo.__name__} {a_coeff} {b_coeff} at {datetime.now() - start}')

        # Call the algorithm function
        st = datetime.now()
        value = algorithms.solve(a_coeff, b_coeff, poly_range, algo)
        

        algo_times.append( (datetime.now() - st).total_seconds() )

        # Loop through all the postproc functions defined in postproc.py
        for fn in funcs:
            
            # print(f'a:{a_coeff} b:{b_coeff} fn:{fn.__name__} value:{value}')
            # logger.debug(f'[{datetime.now() - start}] a:{a_coeff} b:{b_coeff} fn:{fn.__name__} value:{value}')

            # run the algo value through the postproc function
            st = datetime.now()

            # If we are configued to run the postproc functions, do so
            # otherwise, just use the value from above and identify
            # the postproc function as identity() type_id == 0
            if config.run_postproc_functions:
                result = fn(value) # run the postproc function against the value
            else:
                fn.type_id = 0 # identity function
                result = value

            post_times.append( (datetime.now() - st).total_seconds() )

            # If the result we have is in the black list, don't store it
            if black_list and result in black_list or mpmath.isnan(result) or mpmath.isinf(result):
                continue

            # complex numbers not supported yet
            if isinstance(result, mpmath.mpc):
                continue

            # store the result in the hashtable along with the
            # coefficients and other arguments that generated it
            algo_data = (algo.type_id, fn.type_id, result, serialized_range, a_coeff, b_coeff)

            # verify = reverse_solve(algo_data)
            # assert(verify == result)

            # Send the result and data to Redis
            redis_start = datetime.now()
            db.set(result, algo_data)
            redis_times.append( (datetime.now() - redis_start).total_seconds() )

            # also store just the fractional part of the result
            fractional_result = mpmath.frac(result)
            if black_list and fractional_result in black_list or mpmath.isnan(fractional_result) or mpmath.isinf(fractional_result):
                continue
            
            redis_start = datetime.now()
            db.set(fractional_result, algo_data)
            redis_times.append( (datetime.now() - redis_start).total_seconds() )

            # if we aren't calling postproc functions, bail out here
            if not config.run_postproc_functions:
                break

        # logger.debug(f'Algo+Post for {algo.__name__} {a_coeff} {b_coeff} done at {datetime.now() - start}')
    
    elapsed = datetime.now() - start

    logger.info(f'algo: {sum(algo_times)} post: {sum(post_times)} redis: {sum(redis_times)}')
    # return test

        

def reverse_solve(algo_data):
    '''
    Takes the data we are going to store and solves it to 
    verify we get the result back
    '''
    ht = data.DecimalHashTable(0)
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

@app.task()
def check_match(lhs_val, rhs_val):
    logger.info(f'Checking for match at {mpmath.mp.dps} places ...')
    # Since we want more precision, also expand the polynomial range 10x
    # for the continued fraction (or whatever algorithm it used)
    # for the right hand side
    rhs_algo = list(eval(rhs_val))
    poly_range = eval(rhs_algo[3]) # unpack the range
    poly_range = (poly_range[0] * -10, poly_range[1] * 10) # expand it
    rhs_algo[3] = bytes(repr(poly_range), 'utf-8') # re-pack the range

    # solve both sides with the new precision
    lhs = mpmath.fabs(reverse_solve(eval(lhs_val)))
    rhs = mpmath.fabs(reverse_solve(rhs_algo))

    # if there is a match, save it
    if str(lhs)[:mpmath.mp.dps - 2] == str(rhs)[:mpmath.mp.dps - 2]:
        return (lhs_val, rhs_val)
    else:
        return None

if __name__ == '__main__':

    db = 14 # unused database
    precision = 8
    black_list = []


    #zero
    store(db, precision, 'continued_fraction', [(0,0,0)], [(0,0,0)], '(0,200)', black_list)

    # phi
    store(db, precision, 'continued_fraction',[(1,0,0)], [(1,0,0)], '(0,200)', black_list)

    a = []
    b = []
    a_range = [[ [1,4], [0,2], [0,1] ]]
    b_range = [[ [0,2], [-1,1], [0,1] ]]
    for a_coeff, b_coeff in algorithms.iterate_coeff_ranges(a_range, b_range):
        a.append(a_coeff)
        b.append(b_coeff)

    store(db, precision, 'continued_fraction', a, b, '(0,200)', black_list)

    store(db, precision, 'rational_function', [(0,1,0)], [(1,0,0)], mpmath.e, black_list)