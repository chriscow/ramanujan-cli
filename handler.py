import os
import json
import algorithms
import redis
import dotenv
import algorithms
import mpmath
from mpmath import mpf

def generate(event, context):

    db = redis.StrictRedis(host=os.getenv('REDIS_HOST'),
        port=os.getenv('REDIS_PORT'),
        db=0)

    for record in event['Records']:
        payload=record["body"]
        print(str(payload))
        dotenv.load_dotenv()

    e = algorithms.continued_fraction(range(3, 50), range(-1, -48, -1))
    db.lpush(mpf(e).__repr__(), "(1, (3, 1, 2), (4, 5, 6))")
        




def calculate(event, context):

    for record in event['Records']:
        record = json.loads(record['body'])
        algo = getattr(algorithms, record['algo'])
        a_coeffs = json.loads(record['a_coeffs'])
        b_coeffs = json.loads(record['b_coeffs'])
        x = json.loads(record['x'])

        results = []

        coeff_list = zip(a_coeffs, b_coeffs)

        for a_coeff, b_coeff in coeff_list:
            result = algorithms.solve(a_coeff, b_coeff, range(*x), algo)
        
            # store the fraction result in the hashtable along with the
            # coefficients that generated it
            algo_data = (algo.type_id, a_coeff, b_coeff)


            results.append( (result.__repr__(), algo_data) )
    
    response = {
        "statusCode": 200,
        "body": json.dumps(results)
    }

    return response

    # Use this code if you don't use the http event with the LAMBDA-PROXY
    # integration
    """
    return {
        "message": "Go Serverless v1.0! Your function executed successfully!",
        "event": event
    }
    """

if __name__ == '__main__':
    import requests

    # url = 'https://aq4zd2oqsf.execute-api.us-west-2.amazonaws.com/dev/algos/calculate'
    event = {'Records':[
        {'body':'{"algo": "continued_fraction", "a_coeffs": "[[3,1,0]]", "b_coeffs": "[[0,-1,0]]", "x": "[0,200]"}'}
        ]}
    response = calculate(event, None)
    assert(response['statusCode'] == 200)

    body = json.loads(response['body'])
    assert(body[0][0] == "mpf(\'2.7182818284590451\')")
    assert(body[0][1] == [1, [3, 1, 0], [0, -1, 0]])

    event = {'Records':[{'body':'hi mom'}]}
    generate(event, None)

    print('success')