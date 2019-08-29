import os
import redis
import dotenv
import mpmath
from mpmath import mpf   # replacement for Decimal


'''
Implements a hashtable for Decimal values. This is barely an extension of the 
dict type to support Decimal with a defined decimal accuracy as keys.

Some more features are supplied, such as dynamic accuracy (the stored keys' 
accuracy may be redefined), support for serialization by dill/pickle and 
(perhaps) more.
'''
# TODO: might be possible to enhance efficiency by using dec.quantize to round to the required accuracy
# TODO: IMPORTANT! We're exposed to num. errs. A "rounding" func is needed. Here and in "compare_dec_with_accuracy".
class DecimalHashTable():
    """Hashtable with decimal keys. Supports an arbitrary and varying precision for the keys."""
    
    def __init__(self, db, accuracy=8):

        CONFIG_DB = int(os.getenv('CONFIG_DB'))

        self.config = redis.Redis(host=os.getenv('REDIS_HOST'),  port=os.getenv('REDIS_PORT'), db=CONFIG_DB)
        self.redis = redis.Redis(host=os.getenv('REDIS_HOST'),  port=os.getenv('REDIS_PORT'), db=db)

        if self.accuracy is None:
            self.set_accuracy(accuracy)


    def get_accuracy(self):
        accuracy = self.config.get('accuracy')
        return accuracy


    def set_accuracy(self, value):
        current = self.get_accuracy()

        self.config.set('accuracy', value)

        # If the accuracy was not previously set, or is the same value then 
        # there is no history to update.
        if current is None or current == value:
            return
        
        if current not in self.get_history():
            self.config.lpush('accuracy_history', current)


    accuracy = property(get_accuracy, set_accuracy)


    def get_history(self):
        return self.config.lrange('accuracy_history', 0, -1)


    def _manipulate_key(self, key):
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

        # We are going to create an array of keys of varying decimal places of
        # accuracy based on 'accuracy_history'.  The original key passed in is
        # truncated to the number of digits in 'accuracy_history' and then padded
        # with zeros if necessary.
        #
        # The resulting 'old_keys' array is in chronological order of the
        # accuracy history.
        #
        # Numeric values are stored in redis as binary strings.  We need to convert
        # them back to ints
        acc = int(self.get_accuracy())
        history = [int(i) for i in self.get_history()]

        old_keys = [ key_str[:dec_point_ind + i + 1] + '0' * (i - (len(key_str) - dec_point_ind))
                     for i in history ]

        cur_key = key_str[:dec_point_ind + acc + 1] + '0' * (acc - (len(key_str) - dec_point_ind))

        return old_keys, cur_key

    def keys(self, pattern='*'):
        return self.redis.keys(pattern)

    def get(self, key, default=None):
        '''
        Checks the cache for a key and returns the contents if it exists
        otherwise it returns the default value

        Arguments:
            key -- key to find in Redis (will be normalized)
            default -- value returned if the key doesn't exist

        Returns:
            List of items stored with the cache key otherwise the default value
        '''
        if isinstance(key, mpf):
            if mpmath.isnan(key):
                return default

            if mpmath.isinf(key):
                return default

        # Normalize the key
        old_keys, cur_key = self._manipulate_key(key)

        # Dig through the old keys to see if we have a match
        for k in old_keys:
            val = self.redis.lrange(k, 0, -1)
            if val:
                return val
        
        # And now the current key
        val = self.redis.lrange(cur_key, 0, -1)
        if val:
            return val
        
        # If we made it here, there was no match so return the default value
        return d


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
        old_keys, cur_key = self._manipulate_key(key)

        value = bytes(value.__repr__(), 'utf-8')

        # add the value to the current key if it's not there already
        values = self.redis.lrange(cur_key, 0, -1)  # get all list values
        if value not in values:
            self.redis.lpush(cur_key, value)

        # add the value to all previous keys if it's not in any of them either
        for key in old_keys:
            values = self.redis.lrange(key, 0, -1)
            if value not in values:
                self.redis.lpush(key, value)

        return value


if __name__ == '__main__':

    from dotenv import load_dotenv
    load_dotenv()

    ht = DecimalHashTable()
    ht.redis.flushall()

    value = (1, (2,3,4), (5,6,7))
    value2 = (2, (3,4,5), (6,7,8))

    key = mpf(111)
    ht.accuracy = 1
    ht.set(key, value)
    keys = ht.keys()
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

    history = ht.get_history()
    assert(len(history) == 2), 'History should be 2 at this point'

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
    
    
    keys = ht.keys()
    assert(b'111.00' in keys)
    assert(b'111.0' in keys)

    assert(ht.accuracy == b'2')  

    try:
        ht.get(1234)  # invalid key
    except TypeError:
        pass # expected

