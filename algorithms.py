import itertools, mpmath
from mpmath import mpf
from enum import IntEnum

class AlgorithmType(IntEnum):
    ContinuedFraction=1


def range_length(coeff_range, current=1):
    for ar in coeff_range:
        for r in ar:
            current *= (r[1] - r[0])
    
    return current


def coefficients(coeff_range):
    """
    Creates an iterator that goes through all possibilities of coeff_range.
    """
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


def solve(a_coeff, b_coeff, poly_range, algo):
    """
    Simply iterates through all posibilities of coefficients and
    runs the supplied algorithm with each value and yields the result.
    """
    
    # for each coefficient combination, solve the polynomial for x 0 => depth
    if isinstance(poly_range, mpf):
        x = poly_range
        a_poly = solve_polynomial(a_coeff, x)
        b_poly = solve_polynomial(b_coeff, x)
    else:
        a_poly = [solve_polynomial(a_coeff, x) for x in poly_range]
        b_poly = [solve_polynomial(b_coeff, x) for x in poly_range]

    return algo(a_poly, b_poly)
        

def rational_function(a, b):
    """
    """
    return mpf(a / b) if b != 0 else mpmath.nan 

rational_function.type_id = 2

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
        # if the first element of b[] is zero, it wipes out everything else
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

if __name__ == "__main__":
    #
    # just run this file to run the smoke tests:
    #
    #   python algorithms.py
    #

    # test solve_polynomial
    # 1 + 2x + 3x^2 where x = 5
    # 1 + 10 + 3 * 25 = 11 + 75 = 86
    res = solve_polynomial([1,2,3], 5)
    assert (res == 86), f'Expected {res} == 86'

    coeff_iter = coefficients([[ [-4,4], [-3,3], [-2,2] ]])
    res = sum([solve_polynomial(coeff[0], 7) for coeff in coeff_iter])
    assert (res == -5472), f'Expected {res} == -5472'

    # test that we can calculate e
    e = continued_fraction(range(3, 50), range(-1, -48, -1))
    assert (mpmath.e == e), f'Expected {e} == {mpmath.e}'
    
    # test that we can calculate phi
    res = continued_fraction([1] * 50)
    assert (mpmath.phi == res), f'Expected {mpmath.phi} == {res}'

    print('All algorithms tests passed')