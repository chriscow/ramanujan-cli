import os
import itertools
import time
from datetime import datetime
import logging
import mpmath
from mpmath import mpf, mpc
from redis import Redis
from rq import Queue
from rediscluster import RedisCluster

import algorithms
import config
import jobs
import postproc
import utils

log = logging.getLogger(__name__)

from data.wrapper import HashtableWrapper

def run():

    db = HashtableWrapper('match')

    output = []


    postprocs = utils.get_funcs(postproc)
    algos = utils.get_funcs(algorithms)

    rhs_cache = set()

    index = 0
    total = db.size()

    count = 0

    # By the time we reach here, if there were any high-precision matches, 
    # dump out the data to the screen
    mpmath.mp.dps = 15 # back to default
    for match_keys in db.scan():
        for match_key in match_keys:
            
            lhs,rhs = eval(db.redis.get(match_key))

            # algo.type_id, fn.type_id, result, repr(args), a_gen, b_gen

            _, lhs_algo_id, lhs_post, lhs_result, lhs_args, lhs_a_gen, lhs_b_gen = lhs
            _, rhs_algo_id, rhs_post, rhs_result, rhs_args, rhs_a_gen, rhs_b_gen = rhs

            # print('')
            # print('-' * 60)
            # print('')

            lhs_output = ''
            rhs_output = ''



            #
            # output the fancy version for known functions
            #
            if lhs_algo_id == 0: # rational_function
                lhs_args = lhs_args # these are the arguments to the rational_function

                numerator = lhs_args[0][0]
                denominator = lhs_args[1][0]

                # Unpack to get the constant
                # sequence generator function name and args
                _, func_name, func_args = lhs_a_gen.split(':')
                func_args = eval(func_args)
                if func_name == 'polynomial_sequence':
                    poly_range, poly_x_values = func_args
                    const = poly_x_values[0]
                    
                post = postprocs[lhs_post].__name__ + f'( {const} ) == '
                if lhs_post == 0: #identity
                    post = ''

                s = str(lhs_result)
                if lhs_result in utils.const_map:
                    s = f'{utils.const_map[lhs_result]} = {lhs_result}'

                # l = int(mpf(lhs_result))
                # r = int(mpf(rhs_result))
                # if r - l != 0:
                #     if r - l < 0:
                #         s += f' - {mpmath.fabs(r - l)}'
                #     else:
                #         s += f' + {r - l}'

                lhs_result = s
                
                if denominator != 1:
                    lhs_output = f'LHS: {post} {lhs_result}  ==>  {numerator} / {denominator}'
                else:
                    lhs_output = f'LHS: {post} {lhs_result}'
            else:
                # Unpack to get the constant
                # sequence generator function name and args
                func_name, func_args = lhs_a_gen
                func_args = eval(func_args)
                if func_name == 'polynomial_sequence':
                    poly_range, poly_x_values = func_args
                    const = poly_x_values
                    
                lhs_output = f'LHS: const:{const} {postprocs[lhs_post].__name__}( {algos[lhs_algo_id].__name__} (a:{lhs_a_gen} b:{lhs_b_gen}))'

            # sequence_pairs = generate_sequences(rhs_a_gen, rhs_b_gen)
            # a, b = sequence_pairs[rhs_seq_idx]
            a, b = rhs_args

            if rhs_algo_id == 1: # continued fraction
                cont_frac = utils.cont_frac_to_string(a, b)
                post = postprocs[rhs_post].__name__ + '(x) <== '
                if rhs_post == 0: #identity
                    post = ''

                rhs_output = f'RHS: {rhs_result} == {post} {cont_frac}'
            elif rhs_algo_id == 2: # nested radical
                nest_rad = utils.nested_radical_to_string(a, b)
                post = postprocs[rhs_post].__name__ + '(x) <== '
                if rhs_post == 0: #identity
                    post = ''
                
                rhs_output = f'RHS: {rhs_result} == {post} {nest_rad}'

            else:
                rhs_output = f'RHS: {rhs_result} {postprocs[rhs_post].__name__}( {algos[rhs_algo_id].__name__} (a:{rhs_a_gen} b:{rhs_b_gen})) for x => poly range:{poly_range}'
            
            if rhs_output in rhs_cache:
                # print('DUPLICATE:')
                continue

            # print(lhs_output)
            output.append(lhs_output)
            output.append('\n')
            # print(rhs_output)
            output.append(rhs_output)
            # output.write('\n')

            rhs_cache.add(rhs_output)
            # print()
            output.append('\n\n')
            count += 1
            index += 1
            utils.printProgressBar(index, total, prefix=f'Building output {index} / {total}')
    
    i = 0
    filename = f'search-{i}.result.txt' 
    while os.path.exists(filename):
        i += 1
        filename = f'search-{i}.result.txt' 

    out = open(filename, 'w')
    for line in output:
        out.write(line)

    print()
    print(f'Wrote {count} matches at {mpmath.mp.dps} decimal places in {filename}')
    print()
    out.close()
