import os
import inspect
import dotenv

import algorithms
import config
import data
import postproc

import mpmath

import multiprocessing
from multiprocessing import Process
from subprocess import Popen, DEVNULL

def add(a, b):
    return a + b


def spawn_workers():
    '''
    Spawns worker subprocesses based on CPU count.

    Returns:
        Array of process objects
    '''
    workers = []
    cores = multiprocessing.cpu_count()
    for core in range(cores):
        workers.append(Popen(['rq', 'worker'], stdout=DEVNULL, stderr=DEVNULL))

    return workers


from celery import Celery
dotenv.load_dotenv()
REDIS_CELERY_BROKER = os.getenv('REDIS_CELERY_BROKER')
REDIS_CELERY_BACKEND = os.getenv('REDIS_CELERY_BACKEND')
app = Celery('jobs', backend=REDIS_CELERY_BACKEND, broker=REDIS_CELERY_BROKER)
dotenv.load_dotenv()

@app.task
def calculate(a_coeffs, b_coeffs, poly_range):
    
    db = data.DecimalHashTable()

    rhs_algo   = config.rhs.algorithm

    coeff_list = zip(a_coeffs, b_coeffs)
        
    for a_coeff, b_coeff in coeff_list:
        value = algorithms.solve(a_coeff, b_coeff, poly_range, rhs_algo)
    
        # get all the functions in the postproc module
        funcs = [value for name,value in inspect.getmembers(postproc) if inspect.isfunction(value)]

        for fn in funcs:
            
            # run the algo value through the postproc function
            result = fn(value)

            if result in config.rhs.black_list or mpmath.isnan(result) or mpmath.isinf(result):
                continue

            # store the fraction result in the hashtable along with the
            # coefficients that generated it
            algo_data = (rhs_algo.type_id, fn.type_id, a_coeff, b_coeff)
            db.set(result, algo_data)

            # also store just the fractional part of the result
            result = result - int(result)
            db.set(result, algo_data)

if __name__ == '__main__':

    #zero
    calculate([(0,0,0)], [(0,0,0)], range(0,200))

    # phi
    calculate([(1,0,0)], [(1,0,0)], range(0,200))