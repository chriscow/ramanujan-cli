import mpmath
from mpmath import mpf, mpc

import algorithms

# set the decimal precision (not hashtable precision)
mpmath.mp.dps = 15  # 15 decimal places is the default for mpmath anyway but you can change it here


# just an empty object we can hang properties off of dynamically
class Config(object): pass

hash_precision = 10

min_workqueue_size = 10
max_workqueue_size = 100 # maximum jobs in flight per worker before we wait for them to finish
job_result_ttl=60 * 30 # longest amount of time before you check on a job's (complete) status


# Python list of interesting constants.
# Be sure each constant in the list is wrapped in quotes to preserve precision
constants = [ 'mpmath.sqrt(3)', 'mpmath.phi', 'mpmath.e']

verify_finds = [ 'mpmath.sqrt(3)', 'mpmath.phi', 'mpmath.e']


# # # # # #
#
# Left Hand Side
#
# # # # # #

lhs = {
    "algorithms": [algorithms.rational_function],

    # Take the left-side algorithm result and run it through all the functions in postproc.py
    # and save those values too.  Takes much longer though
    "run_postproc": False,

    # If the algorithm (or postproc functions) results in any of these values, 
    # don't store it
    "black_list": set([-2, -1, 0, 1, 2]),

    "a_sequences": [
        {
        "generator": algorithms.polynomial_sequence,
        "arguments": [ [[ [0,1], [1,2], [0,1] ]], None ]
        }
    ],

    "b_sequences": [
        {
        "generator": algorithms.polynomial_sequence,
        "arguments": [ [[ [1,2], [0,1], [0,1] ]], None ]
        }
    ]
}

# # # # # #
#
# Right Hand Side
#
# # # # # #

rhs = {
    "algorithms": [algorithms.nested_radical, algorithms.continued_fraction],

    # Take the left-side algorithm result and run it through all the functions in postproc.py
    # and save those values too.  Takes much longer though
    "run_postproc": False,

    # If the algorithm (or postproc functions) results in any of these values, 
    # don't store it
    "black_list": set([-2, -1, 0, 1, 2]),

    # continued fraction for e
    # rhs.a_range = [[ [3,4], [1,2], [0,1] ]] 
    # rhs.b_range = [[ [0,1], [-1,0], [0,1] ]]

    # finds phi for BOTH continued fraction and nested radical
    # rhs.a_range = [[ [1,2], [0,1], [0,1] ]] 
    # rhs.b_range = [[ [1,2], [0,1], [0,1] ]]

    # just enough range to generate BOTH phi and e
    # rhs.a_range = [[ [1,4], [0,2], [0,1] ]]
    # rhs.b_range = [[ [0,2], [-1,1], [0,1] ]]

    # Finds sqrt(3)
        # "a_sequence": {
        #     "generator": algorithms.integer_sequence,
        #     "arguments": ( [1,2], 2, 50, [1], 1 )
        # },

        # "b_sequence": {
        #     "generator": algorithms.polynomial_sequence,
        #     "arguments": ([[ [1,2], [0,1], [0,1] ]], range(0, 101))
        # }

    "a_sequences": [  # Sequence lengths all need to match (b can be + 1 in length)
        {
            "generator": algorithms.integer_sequence, # integer sequence of 201 digits:
            "arguments": ( [1,2], 2, 100, [1], 1 )    # 2 digit repeating 100x sequence plus a single
        },
        {
            "generator": algorithms.polynomial_sequence,
            "arguments": ([[ [1,4], [0,2], [0,1] ]], range(0, 201))
        }
    ],

    "b_sequences": [
        {
            "generator": algorithms.polynomial_sequence,
            "arguments": ([[ [0,2], [-1,1], [0,1] ]], range(0, 201))
        },
    ]
}

