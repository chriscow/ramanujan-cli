from datetime import datetime
import json
import mpmath
from mpmath import mpf
import redis
import boto3
import algorithms

# {'algo':rhs['algorithm'], 'a_coeffs':a, 'b_coeffs':b, 'x':poly_range}

def calculate(event, context):

    endpoint_url = 'https://sqs.us-west-2.amazonaws.com/'
    queue_url = 'https://sqs.us-west-2.amazonaws.com/148405772863/ramanujan-calculate'
    
    start = datetime.now()
    
    db = redis.Redis(host='ramanujan.afnsuz.0001.usw2.cache.amazonaws.com', port=6379)
    print(f'init redis {datetime.now() - start}')
    count = 0
    
    for record in event['Records']:
        
        print(f'handling record {datetime.now() - start}')
        
        if isinstance(record['body'], str):
            record = json.loads(record['body'])
        else:
            record = record['body']

        algo = getattr(algorithms, record['algo'])
        a_coeffs = record['a_coeffs']
        b_coeffs = record['b_coeffs']
        x = record['x']

        coeff_list = zip(a_coeffs, b_coeffs)

        for a_coeff, b_coeff in coeff_list:
            result = algorithms.solve(a_coeff, b_coeff, range(*x), algo)
        
            # store the fraction result in the hashtable along with the
            # coefficients that generated it
            algo_data = (algo.type_id, a_coeff, b_coeff)
            
            # Convert the result to a key (fixed decimal places)
            old_keys, cur_key = manipulate_key(result)
            
            # This is what we store with the result
            value = algo_data.__repr__()
            
            # Get all existing results for this key and see if we already have it
            values = db.lrange(cur_key, 0, -1)
            if not value in values:
                print(f'begin push {datetime.now() - start}')
                db.lpush(cur_key, algo_data.__repr__())
                print(f'end push {datetime.now() - start}')
                count += 1

    return {
        'statusCode': 200,
        'body': json.dumps({"count":count})
    }

def manipulate_key(key, accuracy=8):
    """Converts the key to a string of the appropriate length, to be used as a key."""

    # The key needs to either be a decimal (mpf) data type or a string.
    if not isinstance(key, mpf) and not isinstance(key, str):
        # raise TypeError('Only Decimal is supported')
        raise TypeError('Only mpmpmath.mpf is supported')

    # Convert the key to a string, if it isn't already
    if isinstance(key, str):
        key_str = key
    else:
        key_str = str(mpmath.fabs(key))

    # Get the index of the decimal point in the string 
    dec_point_ind = key_str.find('.') + 1 if '.' in key_str else 0

    # We are going to create an array of keys of varying decimal places of
    # accuracy based on 'accuracy_history'.  The original key passed in is
    # truncated to the number of digits in 'accuracy_history' and then padded
    # with zeros if necessary.
    #
    # The resulting 'old_keys' array is in chronological order of the
    # accuracy history.
    #old_keys = [ key_str[:dec_point_ind + i + 1] + '0' * (i - (len(key_str) - dec_point_ind))
    #             for i in self.accuracy_history ]
    old_keys = []
    
    cur_key = key_str[:dec_point_ind + accuracy + 1] + '0' * (accuracy - (len(key_str) - dec_point_ind))

    return old_keys, cur_key
    
    a_range    = config.rhs.a_range
    b_range    = config.rhs.b_range
    poly_range = config.rhs.polynomial_range
    rhs_algo   = config.rhs.algorithm

    total_work = algorithms.range_length(b_range, algorithms.range_length(a_range))
    
    start = datetime.datetime.now()

    current = 1

    for a_coeff, b_coeff in algorithms.iterate_coeff_ranges(a_range, b_range):

        result = algorithms.solve(a_coeff, b_coeff, poly_range, rhs_algo)

        if not silent:
            utils.printProgressBar(current, total_work)

        current += 1
        
        # store the fraction result in the hashtable along with the
        # coefficients that generated it
        algo_data = (rhs_algo.type_id, a_coeff, b_coeff)
        save_result(result, algo_data)