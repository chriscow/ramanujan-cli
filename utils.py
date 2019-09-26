import inspect
from algorithms import *
import mpmath
from mpmath import mpf, mpc

const_map = {
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
    print('\r %s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = '\r')


def cont_frac_to_string(a, b, result=None):

    sign = ['+' if i > 0 else '-' for i in b] # get the sign
    b = [mpmath.fabs(i) for i in b]  # now normalize the sign for b (make it positive)

    return """
                    {5}
            {1} {9} ------------
                        {6}
                {2} {10} ------------
                            {7}              = {0}
                    {3} {11} -----------
                                {8}
                        {4} {12} -----------   
                                [...]""".format(result, *a, *b, *sign)

def nested_radical_to_string(a, b, result=None):

    sign = ['+' if i > 0 else '-' for i in b] # get the sign
    b = [mpmath.fabs(i) for i in b]  # now normalize the sign for b (make it positive)
    # [ x if x%2 else x*100 for x in range(1, 10) ]
    b = [i if i != 1 else '' for i in b]

    a = a[:4]
    b = b[:4]
    sign = sign[:4]
    
    return "{0} = √({1} {9} {5}√({2} {10} {6}√({3} {11} {7}√({4} {12} {8}√([ ... ] )))))".format(result, *a, *b, *sign)

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

    s = cont_frac_to_string( (4,1,0), (0,-1,0), f'{numerator} / {denominator}' )
    print(s)

    print()
    s = nested_radical_to_string((1,0,0), (1,0,0))
    print(s)

    print()
    s = nested_radical_to_string((1,0,0), (2,0,0))
    print(s)

    print()
    s = nested_radical_to_string((1,0,0), (-1,0,0))
    print(s)

    print()
    s = nested_radical_to_string((1,0,0), (-2,0,0))
    print(s)

    print('\nLook at the output to be sure utils.py passed')
