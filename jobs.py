import os
import inspect
import dotenv
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

@app.task
def add(a, b):
    return a + b

@app.task
def ping(srctime):
    return srctime

@app.task
def query(algo_name, a_coeffs, b_coeffs, poly_range, black_list):
    
    pass


@app.task()
def store(db, accuracy, algo_name, a_coeffs, b_coeffs, poly_range, black_list):
    
    db = data.DecimalHashTable(db=db, accuracy=accuracy)

    algo = getattr(algorithms, algo_name)

    coeff_list = zip(a_coeffs, b_coeffs)

    poly_range = eval(poly_range)

    start = datetime.now()
    
    algo_times = []
    post_times = []
    redis_times = []

    for a_coeff, b_coeff in coeff_list:

        # logger.debug(f'Starting {algo.__name__} {a_coeff} {b_coeff} at {datetime.now() - start}')

        st = datetime.now()
        value = algorithms.solve(a_coeff, b_coeff, poly_range, algo)
        algo_times.append( (datetime.now() - st).total_seconds() )


        # get all the functions in the postproc module
        funcs = [fn for name,fn in inspect.getmembers(postproc) if inspect.isfunction(fn)]

        for fn in funcs:
            
            # print(f'a:{a_coeff} b:{b_coeff} fn:{fn.__name__} value:{value}')
            # logger.debug(f'[{datetime.now() - start}] a:{a_coeff} b:{b_coeff} fn:{fn.__name__} value:{value}')

            # run the algo value through the postproc function
            st = datetime.now()
            result = fn(value)
            post_times.append( (datetime.now() - st).total_seconds() )

            if black_list and result in black_list or mpmath.isnan(result) or mpmath.isinf(result):
                continue

            # complex numbers not supported yet
            if isinstance(result, mpmath.mpc):
                continue

            # store the fraction result in the hashtable along with the
            # coefficients that generated it
            algo_data = (algo.type_id, fn.type_id, result, poly_range, a_coeff, b_coeff)

            verify = reverse_solve(algo_data)
            assert(verify == result)

            redis_start = datetime.now()
            db.set(result, algo_data)
            # old_keys, cur_key = db.manipulate_key(result)
            # for key in old_keys:
            #     db.setdefault(key, []).append(repr(algo_data))

            # test.setdefault(cur_key, []).append(repr(algo_data))            
            redis_times.append( (datetime.now() - redis_start).total_seconds() )

            # also store just the fractional part of the result
            fractional_result = mpmath.frac(result)
            if black_list and fractional_result in black_list or mpmath.isnan(fractional_result) or mpmath.isinf(fractional_result):
                continue
            
            redis_start = datetime.now()
            db.set(fractional_result, algo_data)
            # old_keys, cur_key = db.manipulate_key(result)
            # for key in old_keys:
            #     test.setdefault(key, []).append(repr(algo_data))

            # test.setdefault(cur_key, []).append(repr(algo_data))            
            redis_times.append( (datetime.now() - redis_start).total_seconds() )

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
    algo_id, postfn_id, result, poly_range, a_coeff, b_coeff = algo_data

    # mpmath.mp.dps *= 2

    algos = utils.get_funcs(algorithms)
    postprocs = utils.get_funcs(postproc)

    algo = algos[algo_id]
    post = postprocs[postfn_id]

    value = algorithms.solve(a_coeff, b_coeff, poly_range, algo)
    value = post(value)

    return value


if __name__ == '__main__':

    db = 15
    precision = 8
    black_list = []


    #zero
    store(db, precision, 'continued_fraction', [(0,0,0)], [(0,0,0)], range(0,200), black_list)

    # phi
    store(db, precision, 'continued_fraction',[(1,0,0)], [(1,0,0)], range(0,200), black_list)

    a = []
    b = []
    a_range = [[ [1,4], [0,2], [0,1] ]]
    b_range = [[ [0,2], [-1,1], [0,1] ]]
    for a_coeff, b_coeff in algorithms.iterate_coeff_ranges(a_range, b_range):
        a.append(a_coeff)
        b.append(b_coeff)

    store(db, precision, 'continued_fraction', a, b, range(0,200), black_list)



    store(db, precision, 'rational_function', [(0,1,0)], [(1,0,0)], mpmath.e, black_list)