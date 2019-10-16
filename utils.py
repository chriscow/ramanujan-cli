import os
import inspect
import mpmath
from mpmath import mpf, mpc
from collections import Iterable
import logging

import algorithms

const_map = {
    mpmath.sqrt(3):'√3',
    mpmath.sqrt(5):'√5',
    mpmath.sqrt(7):'√7',
    mpf(mpmath.phi):'Φ',
    mpf(mpmath.e):'e',
    mpf(mpmath.euler):'ℇ',
    mpf(mpmath.pi):'π',
    mpf(mpmath.euler): 'γ',
    mpf(mpmath.degree): '°',
    mpf(mpmath.catalan): 'catalan',  # actually G
    mpf(mpmath.apery): 'ζ(3)',
    mpf(mpmath.khinchin): 'khinchin',  # actually K
    mpf(mpmath.mertens): 'mertens',   # actually M
    mpf(mpmath.twinprime): 'C₂',
    mpf(mpmath.glaisher): 'glaisher',  # actually A
}

def get_const_str(const):
    if const in const_map:
        return const_map[const]
    

    return str(const)[:15]

# Print iterations progress
def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 30, fill = '█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    total = float(total)

    percent = ("0.0") if total == 0 else ("{0:." + str(decimals) + "f}").format(100 * (iteration / total))
    filledLength = 0 if total == 0 else int(length * iteration // total)

    bar = fill * filledLength + '-' * (length - filledLength)

    output = '\r %s |%s| %s%% %s' % (prefix, bar, percent, suffix)

    console_columns = 80
    padding = ''

    if len(output) < console_columns:
        padding = ' ' * (console_columns - len(output))
    
    suffix = suffix + padding
    print('\r %s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = '\r')


def cont_frac_to_string(a, b):
    
    result = ' = ' + str(algorithms.continued_fraction(a, b))

    a = a[:4]
    b = b[:4]
    sign = ['+' if i > 0 else '-' for i in b] # get the sign
    b = [mpmath.fabs(i) for i in b]  # now normalize the sign for b (make it positive)

    return """
                    {5}
            {1} {9} ------------
                        {6}
                {2} {10} ------------
                            {7}              {0}
                    {3} {11} -----------
                                {8}
                        {4} {12} -----------   
                                [...]""".format(result, *a, *b, *sign)

def nested_radical_to_string(a, b):

    result = str(algorithms.nested_radical(a,b)) + ' = '

    sign = ['+' if i > 0 else '-' for i in b] # get the sign
    b = [mpmath.fabs(i) for i in b]  # now normalize the sign for b (make it positive)
    # [ x if x%2 else x*100 for x in range(1, 10) ]
    b = [i if i != 1 else '' for i in b]

    a = a[:4]
    b = b[:4]
    sign = sign[:4]

    
    return "{0}√({1} {9} {5}√({2} {10} {6}√({3} {11} {7}√({4} {12} {8}√([ ... ] )))))".format(result, *a, *b, *sign)

def polynomial_to_string(coeff, x):

    res = []

    if x in const_map:
        x = const_map[x]
    else:
        x = f'({x})'

    for order in range(len(coeff)):
        if coeff[order] == 0:
            continue

        if order == 0:
            res.append(f'{coeff[order]}')
        elif order == 1:
            res.append(f'{x}')
        
        elif order == 2:
            res.append(f'{coeff[order]}{x}²')
        elif order == 3:
            res.append(f'{coeff[order]}{x}³')
        else:
            res.append(f'{coeff[order]}{x}^{order}')



    res.reverse()
    result = ' + '.join(filter(None, res))  # filter out empty / blanks
    result = result.replace(' + -', ' - ')  # if we are adding a negative, just make it negative
    return result


def get_funcs(module):
    result = {}
    funcs = [fn for name,fn in inspect.getmembers(module) if inspect.isfunction(fn)]
    for fn in funcs:
        if hasattr(fn, 'type_id'):
            type_id = getattr(fn, 'type_id')
            if type_id in result:
                raise Exception(f'Duplicate type id in {module.__name__}')
            result[type_id] = fn

    return result


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

def flatten(lis):
     for item in lis:
         if isinstance(item, Iterable) and not isinstance(item, str):
             for x in flatten(item):
                 yield x
         else:        
             yield item
        
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class CustomConsoleFormatter(logging.Formatter):
    """
    Modify the way DEBUG messages are displayed.

    """
    def __init__(self, fmt="[%(module)s.%(funcName)s] %(asctime)s: %(message)s"):
        logging.Formatter.__init__(self, fmt=fmt)

    def format(self, record):

        if record.levelno == logging.DEBUG:
            record.msg = f'{bcolors.OKGREEN}{record.msg}{bcolors.ENDC}'
        elif record.levelno == logging.INFO:
            record.msg = f'{bcolors.OKBLUE}{record.msg}{bcolors.ENDC}'
        elif record.levelno == logging.WARNING or record.levelno == logging.WARN:
            record.msg = f'{bcolors.WARNING}{record.msg}{bcolors.ENDC}'
        elif record.levelno == logging.ERROR:
            record.msg = f'{bcolors.FAIL}{record.msg}{bcolors.ENDC}'

        # Call the original formatter to do the grunt work
        result = logging.Formatter.format(self, record)

        return result

if __name__ == '__main__':

    s = polynomial_to_string( (0,0,0), mpf(mpmath.e))
    print(s)
    assert(s == '')

    s = polynomial_to_string( (1,0,0), mpf(mpmath.e))
    print(s)

    s = polynomial_to_string( (1,1,0), mpf(mpmath.e))
    print(s)

    s = polynomial_to_string( (-1,1,0), mpf(mpmath.e))
    print(s)

    s = polynomial_to_string( (-1,3,-2), mpf(mpmath.e))
    print(s)

    s = polynomial_to_string( (-7,-3,2,-9), mpf(mpmath.phi))
    print(s)

    numerator = polynomial_to_string( (0,1,0), mpf(mpmath.e))
    denominator = polynomial_to_string( (-2,1,0), mpf(mpmath.e))
    print(f'{numerator} / {denominator} = e / (e - 2)')

    a = algorithms.polynomial_sequence([[ [4,5], [1,2], [0,1] ]], range(0,201))[0]
    b = algorithms.polynomial_sequence([[ [0,1], [-1,0], [0,1] ]], range(0,201))[0]
    s = cont_frac_to_string(a, b)
    print(s)

    print()
    a = [1] * 200
    s = nested_radical_to_string(a, a)
    print(s)

    print()
    b = [2] * 200
    s = nested_radical_to_string(a, b)
    print(s)

    print()
    b = [-1] * 200
    s = nested_radical_to_string(a, b)
    print(s)

    print()
    b = [-2] * 200
    s = nested_radical_to_string(a, b)
    print(s)

    print('\nLook at the output to be sure utils.py passed')

    # Set up a logger
    my_logger = logging.getLogger("my_custom_logger")
    my_logger.setLevel(logging.DEBUG)

    my_formatter = CustomConsoleFormatter()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(my_formatter)
    my_logger.addHandler(console_handler)

    my_logger.debug("This is a DEBUG-level message")
    my_logger.info(bcolors.OKBLUE + "This is an INFO-level message" + bcolors.ENDC)
    my_logger.warning("this is also a warning")
    my_logger.error("this is an error")
    my_logger.exception("this is an exception")