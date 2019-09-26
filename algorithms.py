import itertools, mpmath
from mpmath import mpf, mpc

# The two main algorithms are rational_funciton for the left hand side
# and continued_fraction for the right hand side.
#
# You can make more but be sure to add a type_id that is unique between
# the other functions in this file.

def rational_function(a, b):
    """
    """
    if isinstance(a, list):
        if len(a) > 1:
            raise Exception('rational_function does not take list arguments')
        a = a[0]
    
    if isinstance(b, list):
        if len(b) > 1:
            raise Exception('rational_function does not take list arguments')
        b = b[0]

    return mpf(a / b) if b != 0 else mpmath.nan 

rational_function.type_id = 0


def continued_fraction(a, b=None):
    """
    Parameters:
        a - a list of additive constant (first element) + denominator values 
            (following elements)

        b - a list of numerator values. If ommited, 1's are used.

    If a and b are given and are of the same length, the additive constant is 
    assumed to be 0 and is all denominators and the result is

        b[0] / (a[0] + (b[1] / (a[1] + (b[2] / a[2] + ...

    otherwise the result is

        a[0] + b[0] / (a[1] + b[1] / (a[2] + b[2] / a[3] ...))
    """
    res = 1

    if b is None:
        b = [1] * (len(a)-1)
    elif len(a) == len(b):

        if b[0] == 0:
            b = b[1:]

    if len(a) == len(b) + 1:
        res = a[-1]
        a = a[:-1]

    if len(a) != len(b):
        raise ValueError(f'Expected len(a) == len(b) a:{len(a)} b:{len(b)}')

    for a_val, b_val in zip(reversed(a), reversed(b)):

        if 0 == res:
            break
        
        res = a_val + b_val / res

    return mpf(res)

continued_fraction.type_id = 1



def nested_radical(a, b):
    '''
    sqrt(a + b * sqrt(a + b * sqrt(a + b * sqrt([ ... ]))))
    https://www.johndcook.com/blog/2013/09/13/ramanujans-nested-radical/
    '''
    root = 1

    for a_val, b_val in zip(reversed(a), reversed(b)):
        root = mpmath.sqrt(b_val * root + a_val)

    return root

nested_radical.type_id = 2


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#                                                                             #
#             The rest of the functions below are just helpers                #
#                                                                             #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

def range_length(coeff_range, current=1):
    '''
    Given a tuple to be used as a parameter for range(), this function returns
    how many elements range() will generate.
    '''
    for ar in coeff_range:
        for r in ar:
            current *= (r[1] - r[0])
    
    return current


def coefficients(coeff_range):
    '''
    Creates an iterator that goes through all possibilities of coeff_range.
    '''
    return itertools.product(*[ itertools.product(*[ range(*r) for r in ra ]) for ra in coeff_range ])


def iterate_coeff_ranges(a_array, b_array):

    # coefficients() returns an iterator that covers all coefficient possibilities
    for a_coeff in coefficients(a_array):
        for b_coeff in coefficients(b_array):    
            yield a_coeff[0], b_coeff[0]



def solve_polynomial(coeffs, x):
    """
    Substitues x in the polynomial represented by the list of coeffs
    Parameters:
        coeffs - array of polynomial coefficients
                 coeffs[0] + coeffs[1]*x + coeffs[2]*x^2 ...

        x      - a value to substitute
    """
    return sum([ mpf(coeffs[j]) * mpf(x) ** j for j in range(len(coeffs))])


def solve(a_coeff, b_coeff, poly_range):
    """
    Simply iterates through all posibilities of coefficients and
    runs the supplied algorithm with each value and yields the result.
    """
    const_type = type(mpmath.e)

    # for each coefficient combination, solve the polynomial for x 0 => depth
    if isinstance(poly_range, mpf) or isinstance(poly_range, const_type):
        constant_value = poly_range # just readability

        a_poly = solve_polynomial(a_coeff, constant_value)
        b_poly = solve_polynomial(b_coeff, constant_value)
    else:
        a_poly = [solve_polynomial(a_coeff, x) for x in range(*poly_range)]
        b_poly = [solve_polynomial(b_coeff, x) for x in range(*poly_range)]

    # a_poly and b_poly are list of polynomial results
    return a_poly, b_poly

def polynomial_sequence(coeff_range, poly_x_values):
    result = []

    # check if we received an instance of mpmath constant
    if isinstance(poly_x_values[0], str):
        const = eval(poly_x_values[0])
        for coeffs in coefficients(coeff_range):
            result.append( solve_polynomial(coeffs[0], const) )
    else:
        for coeffs in coefficients(coeff_range):
            result.append( [solve_polynomial(coeffs[0], x) for x in poly_x_values] )

    return result


def integer_sequence(digits, digits_repeat, count, prefix_digits = [], prefix_repeat = 0):
    """
    Generates all possible integer sequences

    Arguments:
        digits - The digits to use to generate the primary part of the sequence
        digits_repeat - how many digits to use from 'digits' that repeat in the sequence
        count - how many times to repeat the above sequence
        prefix_digits - Just like above but will prefix the sequence with another sequence
        prefix_repeat - how many digits to use from 'prefix_digits' to create the prefix

    Usage:
        To generate the sequence (among similar others):
            3, 1, 2, 1, 2, 1, 2, 1, 2

        for seq in integer_sequence([1,2,3], 2, 4, [3], 1):
            print(seq)

        (3, 1, 1, 1, 1, 1, 1, 1, 1)
        (3, 1, 2, 1, 2, 1, 2, 1, 2) << ---
        (3, 2, 1, 2, 1, 2, 1, 2, 1)  
        (3, 2, 2, 2, 2, 2, 2, 2, 2)
    """
    for prefix in itertools.product(prefix_digits, repeat=prefix_repeat):
        for pattern in itertools.product(digits, repeat=digits_repeat):
            yield prefix + pattern * count
        

if __name__ == "__main__":
    #
    # just run this file to run the smoke tests:
    #
    #   python algorithms.py
    #

    # This block will throw an exception if there is a duplicate type_id
    import utils
    import sys
    algorithms = sys.modules[__name__] # need to refer to 'this' module
    algos = utils.get_funcs(algorithms)
    

    # test solve_polynomial
    # 1 + 2x + 3x^2 where x = 5
    # 1 + 10 + 3 * 25 = 11 + 75 = 86
    res = solve_polynomial([1,2,3], 5)
    assert (res == 86), f'Expected {res} == 86'

    # phi
    a_seq, b_seq = solve((1,0,0), (1,0,0), (0,200))
    res = continued_fraction(a_seq, b_seq)
    assert(res == mpmath.phi)

    # e
    a_seq, b_seq = solve((3,1,0), (0,-1,0), (0,200))
    res = continued_fraction(a_seq, b_seq)
    assert(res == mpmath.e)

    # rational function for e
    a_seq, b_seq = solve((0,1,0), (1,0,0), mpmath.e)
    res = rational_function(a_seq, b_seq)
    assert(res == mpmath.e)

    coeff_iter = coefficients([[ [-4,4], [-3,3], [-2,2] ]])
    res = sum([solve_polynomial(coeff[0], 7) for coeff in coeff_iter])
    assert (res == -5472), f'Expected {res} == -5472'

    # test that we can calculate e
    e = continued_fraction(range(3, 50), range(-1, -48, -1))
    assert (mpmath.e == e), f'Expected {e} == {mpmath.e}'
    
    # test that we can calculate phi
    res = continued_fraction([1] * 50)
    assert (mpmath.phi == res), f'Expected {mpmath.phi} == {res}'

    a = [-6.0, -11.0, -22.0, -39.0, -62.0, -91.0, -126.0, -167.0, -214.0, -267.0, -326.0, -391.0, -462.0, -539.0, -622.0, -711.0, -806.0, -907.0, -1014.0, -1127.0]
    b = [-1.0, -3.0, -7.0, -13.0, -21.0, -31.0, -43.0, -57.0, -73.0, -91.0, -111.0, -133.0, -157.0, -183.0, -211.0, -241.0, -273.0, -307.0, -343.0, -381.0]
    res = nested_radical(a, b)
    assert (mpmath.mp.dps == 15), "The assertion below assumes a 15 digit precision"
    assert (res == mpc(real='0.9601180197880006', imag='-3.1130999018855658'))
    # Paul's algo got this:
    # assert (res == mpc(real='-8.7695632738087319', imag='-5.977884644068614'))

    # Find phi
    a_seq, b_seq = solve((1,0,0), (1,0,0), (0,201))
    res = nested_radical(a_seq, b_seq)
    assert(res == mpf(mpmath.phi))

    # Finds 3  (Ramanujan’s nested radical)
    a_seq, b_seq = solve((1,0,0), (2,1,0), (0,200))
    res = nested_radical(a_seq, b_seq)
    assert(res == 3)

    seq = list(integer_sequence([1,2,3], 2, 4, [3], 1))
    assert(seq == [(3, 1, 1, 1, 1, 1, 1, 1, 1), (3, 1, 2, 1, 2, 1, 2, 1, 2), (3, 1, 3, 1, 3, 1, 3, 1, 3), (3, 2, 1, 2, 1, 2, 1, 2, 1), (3, 2, 2, 2, 2, 2, 2, 2, 2), (3, 2, 3, 2, 3, 2, 3, 2, 3), (3, 3, 1, 3, 1, 3, 1, 3, 1), (3, 3, 2, 3, 2, 3, 2, 3, 2), (3, 3, 3, 3, 3, 3, 3, 3, 3)])

    seq = list(integer_sequence([1,2],2,200,[1],1))
    res = continued_fraction(seq[1])
    assert(res == mpmath.sqrt(3))

    print('All algorithms tests passed')