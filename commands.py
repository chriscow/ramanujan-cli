import os, time, itertools
from datetime import datetime, timedelta
import click
import inspect
import dotenv
import redis

import mpmath
from mpmath import mpf

import algorithms
import config
import data
import jobs
import postproc
import utils


@click.option('--silent', '-s', is_flag=True, default=False)
@click.command()
def search(silent):
    '''
    We want to:
        - make a first pass and find all key matches between the two sides
        - with all matches, 
    '''
    lhs_db = data.DecimalHashTable(db=int(os.getenv('LHS_DB')))
    rhs_db = data.DecimalHashTable(db=int(os.getenv('RHS_DB')))

    lhs_size = lhs_db.redis.dbsize()
    rhs_size = rhs_db.redis.dbsize()

    index = 0
    spinner = '|/-\\'


    search_db = redis.Redis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), db=int(os.getenv('SEARCH_DB')))
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

            if not silent:
                index += 1
                cur_sub += 1
                utils.printProgressBar(cur, lhs_size, prefix=f'{spinner[index % len(spinner)]} {key}', suffix=f'{cur_sub}/{subtotal} {cur}/{lhs_size}      ')


    if not silent:
        print()
        print(f'Found {len(matches)} matches at {mpmath.mp.dps} decimal places ...')


    # 'matches()' contains the arguments where the values matched exactly
    # at 15 decimal places (whatever is in the config)
    #
    # Now lets try matching more decimal places
    bigger_matches = set()

    # Loop over and over, doubling the decimal precision until decimal places 
    # exceeds 100 or until there are no more matches
    while len(matches) and mpmath.mp.dps < 50:
        bigger_matches = set()
        mpmath.mp.dps *= 2  # increase the decimal precision
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

            
            job = jobs.check_match.delay(mpmath.mp.dps, repr(lhs_val), repr(rhs_val))
            work.add(job)

            if not silent:
                count += 1
                utils.printProgressBar(count, len(matches), prefix=f' Queueing {mpmath.mp.dps} places', suffix='     ')

        results = wait(work, silent)

        for result in results:
            if result is None:
                continue
            
            bigger_matches.add( (result[0], result[1]) )
            
        if not silent:
            print()
            print(f'Found {len(bigger_matches)} matches at {mpmath.mp.dps} decimal places ...')
        
        matches = bigger_matches
    
    # By the time we reach here, if there were any high-precision matches, 
    # dump out the data to the screen
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
            cont_frac = utils.cont_frac_to_string(rhs_a_coeff, rhs_b_coeff, rhs_result)
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



@click.option('--rhs', '-r', is_flag=True, default=False, help='Generate only the right hand side data')
@click.option('--lhs', '-l', is_flag=True, default=False, help='Generate only the left hand side data')
@click.option('--debug', '-d', is_flag=True, default=False, help='Runs synchronously without queueing')
@click.option('--silent', is_flag=True, default=False)
@click.command()
def generate(rhs, lhs, debug, silent):
    '''
    This command takes the configured coefficient ranges and divides them up
    for separate processes to work on the smaller chunks.  Each chunk is saved
    in a work queue and the workers pull from that queue until its empty.

    Those workers post their results directly to the hashtable.
    '''
    start = datetime.now()  # keep track of what time we started

    # If neither rhs or lhs options were selected, choose both by default
    if not rhs and not lhs:
        rhs = True
        lhs = True

    lhs_data = data.DecimalHashTable(db=int(os.getenv('LHS_DB')))
    rhs_data = data.DecimalHashTable(db=int(os.getenv('RHS_DB')))

    work = set()

    if rhs: # generate the work items for the right hand side
        jobs = _generate(config.rhs, int(os.getenv('RHS_DB')), False, debug, silent)
        wait(jobs, silent)


    if lhs: # generate the work items for the left hand side
        jobs = _generate(config.lhs, int(os.getenv('LHS_DB')), True, debug, silent)
        wait(jobs, silent)

    print()


def _generate(side, db, use_constants, debug=False, silent=False):
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
    
    work = set()

    if use_constants:
        count = 0

        # Loop through the list of constants in the config file.  The constant
        # value is used for the 'polynomial range' as a single value
        for const in config.constants:

            # queue_work generates several jobs based on the a and b ranges
            jobs = queue_work(db, precision, algo, a_range, b_range, const, black_list, debug=debug, silent=True)
            work |= jobs
            count += 1

            if not silent:
                utils.printProgressBar(count, len(config.constants) + 1, prefix='Queuing constants', suffix='     ')
    else:
        work = queue_work(db, precision, algo, a_range, b_range, repr(config.polynomial_range), black_list, debug=debug, silent=silent)

    return work


def queue_work(db, precision, algo_name, a_range, b_range, poly_range, black_list, debug=False, silent=False):
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
                jobs.store(db, precision, algo_name, a, b, poly_range, black_list)
            else:
                # adding .delay after the function name queues it up to be 
                # executed by a Celery worker in another process / machine
                job = jobs.store.delay(db, precision, algo_name, a, b, poly_range, black_list)
                work.add(job)   # hold onto the job info

            if not silent:
                utils.printProgressBar(count, total_work, prefix=f'Queueing {count}/{total_work}', suffix='     ')

            a = []
            b = []

    # If there are any left over coefficients whos array was not evenly
    # divisible by the batch_size at the end, queue them up also
    if len(a):
        if debug:
            jobs.store(db, precision, algo_name, a, b, poly_range, black_list)
        else:
            job = jobs.store.delay(db, precision, algo_name, a, b, poly_range, black_list)
            work.add(job) 

    return work


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

    while len(work):  # while there is still work to do ...

        completed_jobs = set()  # hold completed jobs done in this loop pass
        elapsed = []  # average the elapsed time for each job

        for job in work:
            
            if job.ready():
                results.append(job.result)
                retries = 3
                while retries > 0:
                    try:
                        job.forget()
                        break
                    except redis.exceptions.ConnectionError:
                        retries -= 1

                completed_jobs.add(job)
                continue
            
        # print(f'completed:{len(completed_jobs)} failed:{len(failed_jobs)}')

        # Removes completed jobs from work
        work = work - completed_jobs

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
    