import datetime, time, multiprocessing

import click        # command line tools
from redis import Redis
from rq import Queue

import mpmath
from mpmath import mpf

import algorithms
import config
import data
import jobs
import utils

from subprocess import Popen, DEVNULL
from algorithms import AlgorithmType

@click.group()
def cli():
    pass


# Tell RQ what Redis connection to use
redis_conn = Redis()
q = Queue(connection=redis_conn)  # no args implies the default queue


ht = data.load_hashtable(config.hashtable_filename)


def save_result(result, algo_data):
    hits = ht.get(result)
    if hits and algo_data in hits:
        return # result already in the hashtable
    
    if hits is None:
        hits = ht.setdefault(abs(result), [])

    hits.append( algo_data )



@click.command()
def quegen():
    '''
    
    '''

    redis_server = Popen(['redis-server'], stdout=DEVNULL, stderr=DEVNULL)

    workers = []
    cores = multiprocessing.cpu_count()
    for core in range(cores):
        workers.append(Popen(['rq', 'worker'], stdout=DEVNULL, stderr=DEVNULL))

    try:
        a_range    = config.rhs.a_range
        b_range    = config.rhs.b_range
        poly_range = config.rhs.polynomial_range

        batch_size = 10

        #total_work = algorithms.range_length(b_range, algorithms.range_length(a_range))

        count = 1
        a = []
        b = []
        work = set()  # set of all work items

        start = datetime.datetime.now()

        print('Queuing calculations...')
        for a_coeff, b_coeff in algorithms.iterate_coeff_ranges(a_range, b_range):

            a.append(a_coeff)
            b.append(b_coeff)
            count += 1

            if count % batch_size == 0:
                job = q.enqueue(jobs.generate, a, b, poly_range)
                work.add(job)
                a = []
                b = []

        if len(a):
            # results = jobs.generate(a, b, poly_range)
            job = q.enqueue(jobs.generate, a, b, poly_range)
            work.add(job) 

        total_work = len(work)
        running = True

        print('Waiting for queued work...')
        while len(work):

            utils.printProgressBar(total_work - len(work), total_work)

            completed_jobs = set()
            failed_jobs = set()

            for job in work:
                status = job.get_status()

                if status == 'started':
                    continue

                if status == 'finished':
                    completed_jobs.add(job)
                    continue
                
                if status != 'queued':
                    failed_jobs.add(job)
                    print(f'Unexpected status for job id:{job.id} status:{status}')
                    continue

            # print(f'completed:{len(completed_jobs)} failed:{len(failed_jobs)}')

            for job in completed_jobs:
                # Each job has more than one result
                for result_list in job.result:
                    result, algo_data = result_list
                    save_result(result, algo_data)

            # Removes completed jobs from work
            work = work - completed_jobs - failed_jobs

            time.sleep(2)
        
        utils.printProgressBar(total_work, total_work)

        data.save_hashtable(ht, config.hashtable_filename)
        end = datetime.datetime.now()
        print(f'Hashtable generated in {end - start}')

    finally:
        redis_server.terminate()
        for worker in workers:
            worker.terminate()



@click.option('--silent', '-s', is_flag=True, default=False)
@click.command()
def generate(silent):

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
        algo_data = (AlgorithmType.ContinuedFraction, a_coeff, b_coeff)
        save_result(result, algo_data)


    stop = datetime.datetime.now()
    data.save_hashtable(ht, config.hashtable_filename)
    
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
                    if algo_type == AlgorithmType.ContinuedFraction:
                        print('RHS:')
                        print(utils.polynomial_to_string(a_coeff, const))
                        print('-' * 50)
                        print(utils.polynomial_to_string(b_coeff, const))

                        print(utils.cont_frac_to_string(result, a, b))
                    else:
                        print(result, val)



if __name__ == '__main__':
    cli.add_command(generate)
    cli.add_command(search)
    cli.add_command(quegen)
    cli()

