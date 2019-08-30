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
app = Celery()
app.config_from_object('celeryconfig')

dotenv.load_dotenv()

@app.task
def query(algo_name, a_coeffs, b_coeffs, poly_range, black_list):
    
    pass

@app.task
def store(db, accuracy, algo_name, a_coeffs, b_coeffs, poly_range, black_list):
    
    db = data.DecimalHashTable(db=db, accuracy=accuracy)

    algo = getattr(algorithms, algo_name)

    coeff_list = zip(a_coeffs, b_coeffs)
        
    for a_coeff, b_coeff in coeff_list:
        value = algorithms.solve(a_coeff, b_coeff, poly_range, algo)
    
        # get all the functions in the postproc module
        funcs = [fn for name,fn in inspect.getmembers(postproc) if inspect.isfunction(fn)]

        for fn in funcs:
            
            # print(f'a:{a_coeff} b:{b_coeff} fn:{fn.__name__} value:{value}')

            # run the algo value through the postproc function
            result = fn(value)

            if black_list and result in black_list or mpmath.isnan(result) or mpmath.isinf(result):
                continue

            # complex numbers not supported yet
            if isinstance(result, mpmath.mpc):
                continue

            # store the fraction result in the hashtable along with the
            # coefficients that generated it
            algo_data = (algo.type_id, fn.type_id, a_coeff, b_coeff)
            db.set(result, algo_data)

            # also store just the fractional part of the result
            result = mpmath.frac(result)
            if black_list and result in black_list or mpmath.isnan(result) or mpmath.isinf(result):
                continue
                
            db.set(result, algo_data)

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