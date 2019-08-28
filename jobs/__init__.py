import algorithms
import config
import redis

from subprocess import Popen, DEVNULL

from algorithms import AlgorithmType

def add(a, b):
    return a + b


def spawn():
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

def generate(a_coeffs, b_coeffs, poly_range):

    rhs_algo   = config.rhs.algorithm

    results = []

    coeff_list = zip(a_coeffs, b_coeffs)
        
    for a_coeff, b_coeff in coeff_list:
        result = algorithms.solve(a_coeff, b_coeff, poly_range, rhs_algo)
    
        # store the fraction result in the hashtable along with the
        # coefficients that generated it
        algo_data = (AlgorithmType.ContinuedFraction, a_coeff, b_coeff)

        results.append( (result, algo_data) )
        # print(result, algo_data)
    
    return results