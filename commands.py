import os, datetime, time
import click
import redis
import rq

import multiprocessing as mp

import algorithms
import config
import jobs
import utils

def f(x):
    return x*x

@click.command()
def spawn():
    cores = mp.cpu_count()
    pool = mp.Pool(processes=cores)

    print(pool.map(f, range(10)))

@click.command()
def generate():
    '''
    This command takes the configured coefficient ranges and divides them up
    for separate processes to work on the smaller chunks.  Each chunk is saved
    in a work queue and the workers pull from that queue until its empty.

    Those workers post their results directly to the hashtable.
    '''
    CONFIG_DB = os.getenv('CONFIG_DB')
    db = redis.Redis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), db=CONFIG_DB)

    a_range    = config.rhs.a_range
    b_range    = config.rhs.b_range
    poly_range = config.rhs.polynomial_range

    batch_size = 1000

    #total_work = algorithms.range_length(b_range, algorithms.range_length(a_range))

    count = 1
    a = []  # holds a subset of the coefficient a-range
    b = []  # holds a subset of the coefficient b-range
    work = set()  # set of all jobs queued up to know when we are done

    start = datetime.datetime.now()  # keep track of what time we started

    print('Queuing calculations...')

    # Loop through all coefficient possibilities
    for a_coeff, b_coeff in algorithms.iterate_coeff_ranges(a_range, b_range):

        a.append(a_coeff)
        b.append(b_coeff)
        count += 1

        # When the list of a's and b's are up to batch_size, queue a job
        if count % batch_size == 0:
            # We are queuing arrays of coefficients to work on
            job = jobs.calculate.apply_async((a, b, poly_range))
            work.add(job)   # hold onto the job info
            a = []
            b = []

    # If there are any left over coefficients whos array was not evenly
    # divisible by the batch_size, queue them up also
    if len(a):
        job = jobs.calculate.delay(a, b, poly_range)
        work.add(job) 

    total_work = len(work)
    running = True

    print('Waiting for queued work...')
    while len(work):  # while there is still work to do ...

        utils.printProgressBar(total_work - len(work), total_work)

        completed_jobs = set()  # hold completed jobs done in this loop pass
        failed_jobs = set()     # same for failed jobs

        for job in work:
            
            if job.ready():
                job.forget() # release the resources in redis to hold the state
                completed_jobs.add(job)
                continue
            
        # print(f'completed:{len(completed_jobs)} failed:{len(failed_jobs)}')

        # Removes completed jobs from work
        work = work - completed_jobs - failed_jobs

        time.sleep(.1)
    
    utils.printProgressBar(total_work, total_work)

    end = datetime.datetime.now()
    print(f'Hashtable generated in {end - start}')



@click.option('--silent', '-s', is_flag=True, default=False)
@click.command()
def slowgen(silent):

    a_range    = config.rhs.a_range
    b_range    = config.rhs.b_range
    poly_range = config.rhs.polynomial_range
    rhs_algo   = config.rhs.algorithm

    total_work = algorithms.range_length(b_range, algorithms.range_length(a_range))
    
    start = datetime.datetime.now()

    current = 1

    for a_coeff, b_coeff in algorithms.iterate_coeff_ranges(a_range, b_range):

        result = algorithms.solve(a_coeff, b_coeff, poly_range, rhs_algo)

        if not silent:
            utils.printProgressBar(current, total_work)

        current += 1
        
        # store the fraction result in the hashtable along with the
        # coefficients that generated it
        algo_data = (rhs_algo.type_id, a_coeff, b_coeff)
        # save_result(result, algo_data)


    stop = datetime.datetime.now()
    # data.save_hashtable(ht, config.hashtable_filename)
    
    if not silent:
        print(f'Hashtable generated in {stop - start}')



@click.option('--silent', '-s', is_flag=True, default=False)
@click.command()
def search(silent):

    consts = config.lhs.constants

    lhs_algo = config.lhs.algorithm
    a_range  = config.lhs.a_range
    b_range  = config.lhs.b_range

    current = 1
    total_work = algorithms.range_length(b_range, algorithms.range_length(a_range))

    for const in consts:

        if not isinstance(const, mpf):
            raise TypeError("Constant value must be mpf(const) type")

        for a_coeff, b_coeff in algorithms.iterate_coeff_ranges(a_range, b_range):

            result = abs(algorithms.solve(a_coeff, b_coeff, const, lhs_algo))

            if result in config.lhs.skip:
                continue

            if not silent:
                utils.printProgressBar(current, total_work)

            current += 1

            if ht.get(result):
                val = ht.get(result)
                for algo_type, a, b in val:
                    if algo_type == algorithms.continued_fraction.type_id:
                        print('RHS:')
                        print(utils.polynomial_to_string(a_coeff, const))
                        print('-' * 50)
                        print(utils.polynomial_to_string(b_coeff, const))

                        print(utils.cont_frac_to_string(result, a, b))
                    else:
                        print(result, val)
