import json
import itertools
import redis
import boto3
from datetime import datetime
import mpmath
from mpmath import mpf

endpoint_url = 'https://sqs.us-west-2.amazonaws.com/'
queue_url = 'https://sqs.us-west-2.amazonaws.com/148405772863/ramanujan-calculate'


def queue_work(event, context):
    
    start = datetime.now()
    print(f'queue_work started {start}')
    
    sqs = boto3.client('sqs', endpoint_url=endpoint_url)

    rhs = event['rhs']
    
    a_range    = json.loads( rhs['a_range'] )
    b_range    = json.loads( rhs['b_range'] )
    poly_range = json.loads( rhs['poly_range'] )
    
    total_work = range_length(b_range, range_length(a_range))
    print(f'total work: {total_work}')

    coeffs_per_message = 1
    messages_per_batch = 10
    
    count = 1
    a = []  # holds a subset of the coefficient a-range
    b = []  # holds a subset of the coefficient b-range

    messages = []
    
    # Loop through all coefficient possibilities
    for a_coeff, b_coeff in iterate_coeff_ranges(a_range, b_range):

        count += 1
        
        # print(f'a_coeff: {a_coeff} b_coeff: {b_coeff} count: {count} messages: {len(messages)} elapsed: {datetime.now() - start}')
        
        a.append(a_coeff)
        b.append(b_coeff)

            
        # When the list of a's and b's are up to batch_size, queue a job
        if count % coeffs_per_message == 0:
            print(f'adding message Id: {count}')
            # We are queuing arrays of coefficients to work on
            body = json.dumps( {'algo':rhs['algorithm'], 'a_coeffs':a, 'b_coeffs':b, 'x':poly_range} )
            messages.append({'Id':str(count), 'MessageBody':body})
            a = []
            b = []
            
        if len(messages) == messages_per_batch:
            print(f'before send_message_batch elapsed: {datetime.now() - start}')
            response = sqs.send_message_batch(QueueUrl=queue_url, Entries=messages)
            print(f'send_message_batch: {response} elapsed: {datetime.now() - start}')
            messages = []

    # If there are any left over coefficients whos array was not evenly
    # divisible by the batch_size, queue them up also
    if len(a):
        print(f'adding {len(a)} final coeffs')
        body = json.dumps( {'algo':rhs['algorithm'], 'a_coeffs':a, 'b_coeffs':b, 'x':poly_range} )
        messages.append({'Id':str(count), 'MessageBody':body})
        
    if len(messages):
        print(f'sending final {len(messages)} messages elapsed: {datetime.now() - start}')
        response = sqs.send_message_batch(QueueUrl=queue_url, Entries=messages)
        print(f'final send_message_batch: {response} elapsed: {datetime.now() - start}')
    
    print(f'queue_work finished elapsed: {datetime.now() - start}')

def coefficients(coeff_range):
    """
    Creates an iterator that goes through all possibilities of coeff_range.
    """
    return itertools.product(*[ itertools.product(*[ range(*r) for r in ra ]) for ra in coeff_range ])


#
# Copied from algorithms.py so I didn't have two file copies in lambda for now
#

def iterate_coeff_ranges(a_array, b_array):

    # coefficients() returns an iterator that covers all coefficient possibilities
    for a_coeff in coefficients(a_array):
        for b_coeff in coefficients(b_array):    
            yield a_coeff[0], b_coeff[0]
            
def range_length(coeff_range, current=1):
    for ar in coeff_range:
        for r in ar:
            current *= (r[1] - r[0])
    
    return current