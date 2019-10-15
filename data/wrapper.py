import os
import config
import dotenv
import hashlib
import logging
import utils
import zlib
import mpmath
from mpmath import mpf, mpc

from redis import Redis, ConnectionPool
from rediscluster import RedisCluster

dotenv.load_dotenv()

log = logging.getLogger(__name__)

redis_pool = ConnectionPool(host=os.getenv('REDIS_HOST'), port=6379)

'''
This simply wraps calls to redis to make it look a little more like a data.

Some more features are supplied, such as dynamic accuracy (the stored keys' 
accuracy may be redefined), support for serialization by dill/pickle and 
(perhaps) more.
'''
# TODO: might be possible to enhance efficiency by using dec.quantize to round to the required accuracy
# TODO: IMPORTANT! We're exposed to num. errs. A "rounding" func is needed. Here and in "compare_dec_with_accuracy".
class HashtableWrapper():
    """Hashtable with decimal keys. Supports an arbitrary and varying precision for the keys."""
    
    def __init__(self, side:

        global redis_pool

        if not isinstance(side, str) or side not in ['lhs', 'rhs', 'match']:
            raise Exception(f'Invalid argument for side: {side}. Expected lhs or rhs')

            
        self.cluster = False
            
        if os.getenv('REDIS_CLUSTER_HOST'):
            startup_nodes = [{"host": os.getenv('REDIS_CLUSTER_HOST'), "port": os.getenv('REDIS_CLUSTER_PORT')}]
            # utils.info(log, f'HashtableWrapper using cluster: {startup_nodes}')
            # = RedisCluster(startup_nodes=startup_nodes, decode_responses=True, skip_full_coverage_check=True)
            self.redis = RedisCluster(startup_nodes=startup_nodes, decode_responses=True, skip_full_coverage_check=True)
            self.cluster = True
        else:
            # utils.info(log, f'HashtableWrapper using local redis')
            self.redis = Redis(connection_pool=redis_pool)

        self._cache = {}
        self.side = side
        self.accuracy = config.hash_precision


    def manipulate_key(self, key, value=None):
        '''
        Converts an mpf() numeric value to a string of length indicated by the
        current accuracy value as well as all previous accuracy values.

        Arguments:
            key -- mpf() numeric value

        Returns:
            old_keys, current_key pair
                old_keys are all previous hashes of the key value
                current_key is the current hash value of the key
        '''

        # The key needs to either be a decimal (mpf) data type or a string.
        if not isinstance(key, mpf) and not isinstance(key, str):
            # raise TypeError('Only Decimal is supported')
            raise TypeError('Only mpmath.mpf is supported')

        # Convert the key to a string, if it isn't already
        if isinstance(key, str):
            key_str = key
        else:
            key_str = str(mpmath.fabs(key))

        # Get the index of the decimal point in the string 
        dec_point_ind = key_str.find('.') + 1 if '.' in key_str else 0

        acc = self.accuracy

        padded_key = key_str[:dec_point_ind + acc] + '0' * (acc - (len(key_str) - dec_point_ind))
        key = self.side + ':' + padded_key

        if value is None:
            key += ':*'
        else:
            if isinstance(value, tuple):
                value = bytes(repr(value), 'utf-8')

            value_hash = hashlib.sha256(value).hexdigest()
            key +=  ':' + value_hash

        return key

    def keys(self, key):
        if isinstance(key, bytes):
            key = key.decode('utf-8')

        if isinstance(key, mpf):
            if mpmath.isnan(key):
                return None

            if mpmath.isinf(key):
                return None

        cur_key = self.manipulate_key(key, value)
        return self.redis.keys(cur_key + '*')

    def values(self, key):
        '''
        Checks the cache for a key and returns the contents if it exists
        otherwise it returns the default value

        Arguments:
            key -- key to find in Redis (will be normalized)
            default -- value returned if the key doesn't exist

        Returns:
            List of items stored with the cache key otherwise the default value
        '''
        
        # And now the current key
        keys = self.keys(key, None)
        for key in keys:
            # compressed = self.redis.get(key)
            # yield zlib.decompress(compressed)
            yield self.redis.get(key)
    

    def scan(self, match=None, count=1000):

        if match is None:
            match = '*'

        match = self.side + ':' + match + ':*'

        if self.cluster:
            for result in self.scan_cluster(match, count):
                yield result
        else:
            cursor = '0'
            while cursor != 0:
                cursor, data = self.redis.scan(cursor=cursor, match=match, count=count)
                yield data

    def scan_cluster(self, match=None, count=1000):
        """
        Make an iterator using the SCAN command so that the client doesn't
        need to remember the cursor position.
        ``match`` allows for filtering the keys by pattern
        ``count`` allows for hint the minimum number of returns
        Cluster impl:
            Result from SCAN is different in cluster mode.
        """
        cursors = {}
        nodeData = {}
        for master_node in self.redis.connection_pool.nodes.all_masters():
            cursors[master_node["name"]] = "0"
            nodeData[master_node["name"]] = master_node

        while not all(cursors[node] == 0 for node in cursors):
            for node in cursors:
                if cursors[node] == 0:
                    continue

                conn = self.redis.connection_pool.get_connection_by_node(nodeData[node])

                pieces = ['SCAN', cursors[node]]
                if match is not None:
                    pieces.extend([b'MATCH', match])
                if count is not None:
                    pieces.extend([b'COUNT', count])

                conn.send_command(*pieces)

                raw_resp = conn.read_response()

                # if you don't release the connection, the driver will make another, and you will hate your life
                self.connection_pool.release(conn)
                cur, resp = self.redis._parse_scan(raw_resp)
                cursors[node] = cur

                yield resp

    def set(self, key, value):
        '''
        Finds the value for the corresponding key in the cache. If the value exists,
        it will be a list of values. If the passed-in value does not exist in the
        list, it will be added.

        Arguments:
            key -- key that will be normalized and searched for in the cache
            value -- value to be added to the key store if it doesn't already exist

        Returns:
            Returns the value passed in
        '''

        if isinstance(key, mpf):
            if mpmath.isnan(key):
                return value

            if mpmath.isinf(key):
                return value
        
        # Normalize the key
        cur_key = self.manipulate_key(key, value)

        value = bytes(repr(value), 'utf-8')
        # value = zlib.compress(bytes(repr(value), 'utf-8'))

        # add the value to the current key if it's not there already
        self._store(cur_key, value)


    def _store(self, key, value):
        # self._cache[key] = value
        self.redis.set(key, value)

    def commit(self):
        pass
        # pipe = self.redis.pipeline(transaction=False)
        # for key in self._cache.keys():
        #     values = pipe.set(key, self._cache[key])

        # self._cache = {}

        # pipe.execute()

if __name__ == '__main__':

    from dotenv import load_dotenv
    load_dotenv()

    ht = HashtableWrapper('lhs')
    ht.redis.flushall()

    value = (1, (2,3,4), (5,6,7))
    value2 = (2, (3,4,5), (6,7,8))

    key = mpf(111)
    ht.accuracy = 1
    ht.set(key, value)
    keys = ht.redis.keys()
    assert(keys[0] == b'111.0')
    test = ht.get(key)
    assert(test[0] == b'(1, (2, 3, 4), (5, 6, 7))')

    ht.accuracy = 2

    # make sure we can still get value if accuracy changes
    test = ht.get(key)
    assert(test[0] == b'(1, (2, 3, 4), (5, 6, 7))')

    ht.accuracy = 3
    test = ht.get(key)
    assert(test[0] == b'(1, (2, 3, 4), (5, 6, 7))')

    # make sure history updates
    ht.accuracy = 2
    history = ht.get_history()
    assert(len(history) == 3), f'History should be 3 at this point, not {len(history)}'

    # set a new value on the same key but accuracy changed.
    # should be reflected in current key plus all historical keys
    test = ht.set(key, value2)
    assert(test == b'(2, (3, 4, 5), (6, 7, 8))')

    values = ht.get(key) # current key
    assert(b'(2, (3, 4, 5), (6, 7, 8))' in values)
    values = ht.get('111.0') # old key
    assert(b'(2, (3, 4, 5), (6, 7, 8))' in values)
    
    
    keys = ht.redis.keys()
    assert(b'111.00' in keys)
    assert(b'111.0' in keys)

    assert(ht.accuracy == b'2')  

    try:
        ht.get(1234)  # invalid key
    except TypeError:
        pass # expected

    print('HashtableWrapper passed')
