import os
import dotenv

import algorithms
import config
import data

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


def calculate(a_coeffs, b_coeffs, poly_range):
    dotenv.load_dotenv()
    
    db = data.DecimalHashTable()

    rhs_algo   = config.rhs.algorithm

    coeff_list = zip(a_coeffs, b_coeffs)
        
    for a_coeff, b_coeff in coeff_list:
        result = algorithms.solve(a_coeff, b_coeff, poly_range, rhs_algo)
    
        # store the fraction result in the hashtable along with the
        # coefficients that generated it
        algo_data = (rhs_algo.type_id, a_coeff, b_coeff)

        db.set(result, algo_data)
