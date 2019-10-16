# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
# *
# *   T I N Y  C O N F I G
# *
# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 


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
constants = ['mpmath.e', 'mpmath.phi']
verify_finds = [ 'mpmath.phi', 'mpmath.e']

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
    "algorithms": [algorithms.continued_fraction],

    # Take the left-side algorithm result and run it through all the functions in postproc.py
    # and save those values too.  Takes much longer though
    "run_postproc": False,

    # If the algorithm (or postproc functions) results in any of these values, 
    # don't store it
    "black_list": set([-2, -1, 0, 1, 2]),

# just enough range to generate BOTH phi and e
# rhs.a_range = [[ [1,4], [0,2], [0,1] ]]
# rhs.b_range = [[ [0,2], [-1,1], [0,1] ]]

    "a_sequences": [  # Sequence lengths all need to match (b can be + 1 in length)
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