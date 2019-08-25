import algorithms
import config

from algorithms import AlgorithmType

def add(a, b):
    return a + b

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