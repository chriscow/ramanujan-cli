import os, datetime
import click, msgpack
import dill as pickle
import config
import utils
from algorithms import range_length, coefficients, solve_polynomial, AlgorithmType
from mpmath import mpf as dec   # replacement for Decimal


def load_hashtable(filename, silent=False):
    
    ht = None
    
    if os.path.isfile(config.hashtable_filename):
    
        start = datetime.datetime.now()

        if not silent:
            print('Loading hashtable ...', end=None, flush=True)
        
        with open(filename, 'rb') as input_file:
            ht = pickle.load(input_file)

        end = datetime.datetime.now()
        if not silent:
            print(f'{end - start}ms')

    else:
        ht = DecimalHashTable(8)

    return ht


def save_hashtable(ht, filename, silent=False):

    with open(filename, 'wb') as output_file:
        pickle.dump(ht, output_file, protocol=pickle.HIGHEST_PROTOCOL)
    

def msgpack_encode(obj):

    print(type(obj))

    if isinstance(obj, DecimalHashTable):
        return {'__decimalhashtable__':True, 'state':(obj.accuracy, obj.accuracy_history, dict(obj))}

    return obj


def msgpack_decode(obj):
    if b'__decimalhashtable__' in obj:
        accuracy, history, data = obj['state']
        ht = DecimalHashTable(accuracy)
        ht.accuracy_history = history
        ht.update(data)
        return ht
    
    return obj

"""
Implements a hashtable for Decimal values. This is barely an extension of the 
dict type to support Decimal with a defined decimal accuracy as keys.

Some more features are supplied, such as dynamic accuracy (the stored keys' 
accuracy may be redefined), support for serialization by dill/pickle and 
(perhaps) more.
"""
# TODO: might be possible to enhance efficiency by using dec.quantize to round to the required accuracy
# TODO: IMPORTANT! We're exposed to num. errs. A "rounding" func is needed. Here and in "compare_dec_with_accuracy".
class DecimalHashTable(dict):
    """Hashtable with decimal keys. Supports an arbitrary and varying precision for the keys."""

    def __init__(self, accuracy):
        """accuracy - the required keys accuracy (how many digits should be compared)."""
        # +1 for the decimal point
        self.accuracy = accuracy + 1
        self.accuracy_history = []


    def update_accuracy(self, accuracy):
        """Update the used keys accuracy for new saved values."""
        self.accuracy_history.append(self.accuracy)
        self.accuracy = accuracy + 1

    def _manipulate_key(self, key):
        """Converts the key to a string of the appropriate length, to be used as a key."""

        # The key needs to either be a decimal (mpf) data type or a string.
        if not isinstance(key, dec) and not isinstance(key, str):
            # raise TypeError('Only Decimal is supported')
            raise TypeError('Only mpmath.mpf is supported')

        # Convert the key to a string, if it isn't already
        if isinstance(key, str):
            key_str = key
        else:
            key_str = str(key)

        # Get the index of the decimal point in the string 
        dec_point_ind = key_str.find('.') + 1 if '.' in key_str else 0

        # We are going to create an array of keys of varying decimal places of
        # accuracy based on 'accuracy_history'.  The original key passed in is
        # truncated to the number of digits in 'accuracy_history' and then padded
        # with zeros.
        #
        # The resulting 'old_keys' array is in chronological order of the
        # accuracy history.
        old_keys = [ key_str[:dec_point_ind + i + 1] + '0' * (i - (len(key_str) - dec_point_ind))
                     for i in self.accuracy_history ]

        cur_key = key_str[:dec_point_ind + self.accuracy + 1] + '0' * (self.accuracy - (len(key_str) - dec_point_ind))

        return old_keys, cur_key

    def get(self, k, d=None):
        # Normalize the key
        old_keys, cur_key = self._manipulate_key(k)

        # Dig through the old keys to see if we have a match
        for k in old_keys:
            if super().__contains__(k):
                return super().__getitem__(k)
        
        # And now the current key
        if super().__contains__(cur_key):
            return super().__getitem__(cur_key)
        
        # If we made it here, there was no match so return the default value
        return d

    def setdefault(self, k, d=None):
        """
        Returns the value from the dictionary. If not found, sets the value in 
        the dictionary for this key to the default value.
        """

        # Normalize the key
        old_keys, cur_key = self._manipulate_key(k)

        # Dig through the old keys to see if we have a match
        for k in old_keys:
            if super().__contains__(k):
                return super().__getitem__(k)

        # And now the current key
        if super().__contains__(cur_key):
            return super().__getitem__(cur_key)

        # If we made it here, set the value in the dictionary to the default value
        super().__setitem__(cur_key, d)

        return d

    def __setitem__(self, key, value):
        old_keys, cur_key = self._manipulate_key(key)
        for k in old_keys:
            if super().__contains__(k):
                super().__delitem__(k)
        return super().__setitem__(cur_key, value)

    def __getitem__(self, item):
        old_keys, cur_key = self._manipulate_key(item)
        # The order in which we run here over the keys doesn't matter, since we disallow multiple identical keys in the
        # same length, there will be at most one results.
        for k in old_keys:
            if super().__contains__(k):
                return super().__getitem__(k)
        return super().__getitem__(cur_key)

    def __delitem__(self, key):
        old_keys, cur_key = self._manipulate_key(key)
        for k in old_keys:
            if super().__contains__(k):
                super().__delitem__(k)
        if super().__contains__(cur_key):
            super().__delitem__(cur_key)

    def __contains__(self, item):
        old_keys, cur_key = self._manipulate_key(item)
        for k in old_keys:
            if super().__contains__(k):
                return True
        return super().__contains__(cur_key)

    def __getstate__(self):
        """Used by pickle for serializing."""
        return (self.accuracy, self.accuracy_history, dict(self))

    def __setstate__(self, state):
        """Used by pickle for de-serializing."""
        self.accuracy, self.accuracy_history, data = state
        self.update(data)

    def __reduce__(self):
        """Used by pickle for serializing (I think. Long time, no documentation)."""
        return (DecimalHashTable, (self.accuracy,), self.__getstate__())

    def append_dict(self, appended_dict):
        """Enables appending another dict to this one. May be used to distribute run and join results."""

        if self.accuracy != appended_dict.accuracy:
            raise TypeError('Two dictionaries are of non-fitting accuracies')

        self.accuracy_history += [ a for a in appended_dict.accuracy_history if a not in self.accuracy_history ]
        for k in super(DecimalHashTable, appended_dict).keys():
            if k in super().keys():
                try:
                    orig_items = super().__getitem__(k)
                    appended_items = super(DecimalHashTable, appended_dict).__getitem__(k)
                    if not isinstance(orig_items, list):
                        orig_items = [orig_items]
                    if not isinstance(appended_items, list):
                        appended_items = [appended_items]
                    super().__setitem__(k, orig_items + appended_items)
                except TypeError:
                    type_orig = str(type(super().__getitem__(k)))
                    type_appended = str(type(super(DecimalHashTable, appended_dict).__getitem__(k)))
                    print('types are: original dict: %s, appended dict: %s' % (type_orig, type_appended))
                    raise
            else:
                super().__setitem__(k, super(DecimalHashTable, appended_dict).__getitem__(k))