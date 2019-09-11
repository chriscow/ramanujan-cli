import os, time
import inspect
import itertools
import logging
from datetime import datetime, timedelta

from rq.job import JobStatus

import algorithms
import config
from data.wrapper import HashtableWrapper
import postproc
import utils

import mpmath
from mpmath import mpf


def ping(timestamp):
    return timestamp



def store(db, accuracy, algo_name, a_coeffs, b_coeffs, serialized_range, black_list):
    '''
    This method is queued up by the master process to be executed by a Celery worker.

    It calls the given algorithm with the given arguments and stores the value and
    arguments to arrive at that value in Redis.  Then, if configured, it runs the
    result through all the postproc.py functions to alter the result and stores
    all those too.
    '''

    # The db number passed in indicated whether we are working on the left or right
    db = HashtableWrapper(db=db, accuracy=accuracy)

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
                logging.debug(f'Skipping complex result: {result}')
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
            # fractional_result = mpmath.frac(result)
            # if black_list and fractional_result in black_list or mpmath.isnan(fractional_result) or mpmath.isinf(fractional_result):
            #     continue
            
            # redis_start = datetime.now()
            # db.set(fractional_result, algo_data)
            # redis_times.append( (datetime.now() - redis_start).total_seconds() )

            # if we aren't calling postproc functions, bail out here
            if not config.run_postproc_functions:
                break

        # logger.debug(f'Algo+Post for {algo.__name__} {a_coeff} {b_coeff} done at {datetime.now() - start}')
    
    elapsed = datetime.now() - start

    logging.info(f'algo: {sum(algo_times)} post: {sum(post_times)} redis: {sum(redis_times)}')
    # return test



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
    eta = timedelta()

    utils.printProgressBar(0, total_work, prefix='Waiting ...', suffix='     ')

    results = []
    failed = set()

    while len(work):  # while there is still work to do ...

        completed_jobs = set()  # hold completed jobs done in this loop pass
        elapsed = []  # average the elapsed time for each job

        for job in work:            
            if job.get_status() == JobStatus.FINISHED:
                results.append(job.result)
                completed_jobs.add(job)
            elif job.get_status() == JobStatus.FAILED:
                failed.add(job)


            
        # print(f'completed:{len(completed_jobs)} failed:{len(failed_jobs)}')

        # Removes completed jobs from work
        work = work - completed_jobs - failed

        # Wait a little bit before checking if more work has completed
        time.sleep(.1)

        if not silent:

            # the eta calculation isn't working. Ignore this...
            if len(elapsed):
                # work left / work done on this pass * seconds
                avg_secs = sum(elapsed) / len(elapsed)
                eta = timedelta(seconds = len(work) / len(elapsed) * avg_secs)

            utils.printProgressBar(total_work - len(work), total_work, prefix=f'Waiting {total_work - len(work)}/{total_work}', suffix='     ') # eta not working, suffix=f'ETA: {eta}')
    
    return results
    
        

def reverse_solve(algo_data):
    '''
    Takes the data we are going to store and solves it to 
    verify we get the result back
    '''
    ht = HashtableWrapper(db=0, accuracy=config.hash_precision)

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

    print('jobs.py passed')