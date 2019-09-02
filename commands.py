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


@click.argument('filename')
@click.option('--silent', '-s', is_flag=True, default=False)
@click.command()
def search(filename, silent):
    '''
    We want to:
        - make a first pass and find all key matches between the two sides
        - with all matches, 
    '''
    
    ht = data.DecimalHashTable(0)
    postprocs = utils.get_funcs(postproc)
    algos = utils.get_funcs(algorithms)

    matches = set()

    for key, lhs_vals, rhs_vals in key_matches(silent):

        for lhs_val, rhs_val in itertools.product(lhs_vals, rhs_vals):  
            
            _,_,lhs_result,_,_,_ = eval(lhs_val)
            _,_,rhs_result,_,_,_ = eval(rhs_val)

            lhs = jobs.reverse_solve(eval(lhs_val))
            assert(lhs == lhs_result)

            rhs = jobs.reverse_solve(eval(rhs_val))
            assert(rhs == rhs_result)

            _, lhs_key = ht.manipulate_key(lhs)
            _, rhs_key = ht.manipulate_key(rhs)
            if (lhs_key != rhs_key):
                print(f'key mismatch lhs:{lhs_key} != rhs:{rhs_key}')
            
            if mpmath.fabs(lhs) == mpmath.fabs(rhs):
                matches.add( (lhs_val, rhs_val) )

    if not silent:
        print(f'Found {len(matches)} matches at {mpmath.mp.dps} decimal places ...')

    # Matches contains the arguments where the values matched exactly
    # at 15 decimal places (whatever is in the config)
    #
    # Now lets try matching more decimal places
    while len(matches) and mpmath.mp.dps < 500:
        bigger_matches = set()
        mpmath.mp.dps *= 2
        count = 0
        for lhs_val, rhs_val in matches:

            # expand the polynomial range for the rhs
            rhs_algo = list(eval(rhs_val))
            poly_range = eval(rhs_algo[3])
            poly_range = (poly_range[0] * -10, poly_range[1] * 10)
            rhs_algo[3] = bytes(repr(poly_range), 'utf-8')

            lhs = jobs.reverse_solve(eval(lhs_val))
            rhs = jobs.reverse_solve(rhs_algo)

            if mpmath.fabs(lhs) == mpmath.fabs(rhs):
                bigger_matches.add( (lhs_val, rhs_val) )

            if not silent:
                count += 1
                utils.printProgressBar(count, len(matches), prefix=f' Trying {mpmath.mp.dps} places', suffix='          ')

        if not silent:
            print(f'Found {len(bigger_matches)} matches at {mpmath.mp.dps} decimal places ...')
        
        matches = bigger_matches
    
    for lhs, rhs in bigger_matches:
        lhs_algo_id, lhs_post, lhs_result, const, lhs_a_coeff, lhs_b_coeff = eval(lhs)
        rhs_algo_id, rhs_post, rhs_result, poly_range, rhs_a_coeff, rhs_b_coeff = eval(rhs)

        print('')
        print('-' * 60)
        print('')
        print(f'LHS: const:{const} {postprocs[lhs_post].__name__}( {algos[lhs_algo_id].__name__} (a:{lhs_a_coeff} b:{lhs_b_coeff}))')
        print(f'RHS: {postprocs[rhs_post].__name__}( {algos[rhs_algo_id].__name__} (a:{rhs_a_coeff} b:{rhs_b_coeff})) for x => poly range:{poly_range}')
        print('')
    



    

def key_matches(silent):
    '''
    Searches for keys from the lhs in the rhs.

    Returns:
        Three element array:
            matching key, lhs algo arguments, rhs algo arguments
    '''
    lhs = data.DecimalHashTable(db=int(os.getenv('LHS_DB')))
    rhs = data.DecimalHashTable(db=int(os.getenv('RHS_DB')))

    lhs_size = lhs.redis.dbsize()
    rhs_size = rhs.redis.dbsize()

    cur = 0
    for key in lhs.redis.scan_iter():

        # *hs_vals is a list of algorithm parameters used to generate the result
        lhs_vals = lhs.get(key)
        rhs_vals = rhs.get(key)
        if rhs_vals:
            yield (key, lhs_vals, rhs_vals)

        if not silent:
            cur += 1
            utils.printProgressBar(cur, lhs_size)




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

    if rhs:
        jobs = _generate(config.rhs, int(os.getenv('RHS_DB')), False, debug, silent)
        wait(rhs_data, jobs, silent)


    if lhs:
        jobs = _generate(config.lhs, int(os.getenv('LHS_DB')), True, debug, silent)
        wait(lhs_data, jobs, silent)



def _generate(side, db, use_constants, debug=False, silent=False):

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
        for const in config.constants:
            jobs = queue_work(db, precision, algo, a_range, b_range, const, black_list, debug=debug, silent=True)
            work |= jobs
            count += 1

            if not silent:
                utils.printProgressBar(count, len(config.constants) + 1, prefix='Queuing constants', suffix='          ')
    else:
        work = queue_work(db, precision, algo, a_range, b_range, repr(config.polynomial_range), black_list, debug=debug, silent=silent)

    return work


def queue_work(db, precision, algo_name, a_range, b_range, poly_range, black_list, debug=False, silent=False):
    '''
    Queues the algorithm calculations to be run and stored in the database.
    '''
    batch_size = 100

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
                jobs.store(db, precision, algo_name, a, b, poly_range, black_list)
            else:
                job = jobs.store.delay(db, precision, algo_name, a, b, poly_range, black_list)
                work.add(job)   # hold onto the job info

            if not silent:
                utils.printProgressBar(count, total_work, prefix=f'Queueing {count}/{total_work}', suffix='          ')

            a = []
            b = []

    # If there are any left over coefficients whos array was not evenly
    # divisible by the batch_size, queue them up also
    if len(a):
        if debug:
            jobs.store(db, precision, algo_name, a, b, repr(poly_range), black_list)
        else:
            job = jobs.store.delay(db, precision, algo_name, a, b, repr(poly_range), black_list)
            work.add(job) 

    return work


def wait(ht, work, silent):
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

    # db = data.DecimalHashTable(db=db)    
    # db = dht.DecimalHashTable(config.precision)

    utils.printProgressBar(0, total_work, prefix='Waiting ...', suffix='          ')

    while len(work):  # while there is still work to do ...

        completed_jobs = set()  # hold completed jobs done in this loop pass
        elapsed = []  # average the elapsed time for each job

        for job in work:
            
            if job.ready():
                # for key, values in job.result.items():
                #     for value in values:
                #         ht.set(key, value)

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
        time.sleep(.1)

        if not silent:

            if len(elapsed):
                # work left / work done on this pass * seconds
                avg_secs = sum(elapsed) / len(elapsed)
                eta = timedelta(seconds = len(work) / len(elapsed) * avg_secs)

            utils.printProgressBar(total_work - len(work), total_work, prefix=f'Waiting {total_work - len(work)}/{total_work}', suffix='          ') # eta not working, suffix=f'ETA: {eta}')
    

@click.option('--silent', '-s', is_flag=True, default=False)
@click.command()
def clean(silent):
    '''
    Deletes all data from redis to start from scatch.
    '''
    for i in range(0, 16):
        db = redis.Redis(host=os.getenv('REDIS_HOST'),  port=os.getenv('REDIS_PORT'), db=i)
        result = db.flushdb()

    if not silent:
        print('Redis data deleted')
