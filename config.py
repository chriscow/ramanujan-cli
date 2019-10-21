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
constants = ['mpmath.apery', 'mpmath.khinchin', 'mpmath.glaisher', 
'mpmath.mertens', 

# https://en.wikipedia.org/wiki/Twin_prime#First_Hardy%E2%80%93Littlewood_conjecture
'mpmath.twinprime',

# First Riemann zeta zeros
'14.134725141734693790457251983562470270784257115699243175685567460149',
'21.022039638771554992628479593896902777334340524902781754629520403587',
'25.010857580145688763213790992562821818659549672557996672496542006745',
'30.424876125859513210311897530584091320181560023715440180962146036993',
'32.935061587739189690662368964074903488812715603517039009280003440784',
'37.586178158825671257217763480705332821405597350830793218333001113622',
'40.918719012147495187398126914633254395726165962777279536161303667253',
'43.327073280914999519496122165406805782645668371836871446878893685521',
'48.005150881167159727942472749427516041686844001144425117775312519814',
'49.773832477672302181916784678563724057723178299676662100781955750433',

]

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
        "arguments": [ [[ [0,1], [1,11], [0,7] ]], None ]
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
    "run_postproc": True,

    # If the algorithm (or postproc functions) results in any of these values, 
    # don't store it
    "black_list": set([-2, -1, 0, 1, 2]),

    "a_sequences": [  # Sequence lengths all need to match (b can be + 1 in length)
        {
            "generator": algorithms.integer_sequence, # integer sequence of 201 digits:
            "arguments": ( [1,2,3,4,5,6,7,8,9], 2, 100, [1,2,3,4,5,6,7,8,9], 1 )    # 2 digit repeating 100x sequence plus a single
        },
        {
            "generator": algorithms.polynomial_sequence,
            "arguments": ([[ [-11,11], [-11,11], [-11,11] ]], range(0, 201))
        }
    ],

    "b_sequences": [
        {
            "generator": algorithms.integer_sequence, # integer sequence of 201 digits:
            "arguments": ( [1,2,3,4,5,6,7,8,9], 2, 100, [1,2,3,4,5,6,7,8,9], 1 )    # 2 digit repeating 100x sequence plus a single
        },
        {
            "generator": algorithms.polynomial_sequence,
            "arguments": ([[ [-11,11], [-11,11], [-11,11] ]], range(0, 201))
        }
    ]
}