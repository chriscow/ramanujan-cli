import math
import itertools
from mpmath import mpf as dec

def coefficients(coeff_range):
    """
    Creates an iterator that goes through all possibilities of coeff_range.
    """
    return itertools.product(*[ itertools.product(*[ range(*r) for r in ra ]) for ra in coeff_range ])


def solve_polynomial(coeffs, x):
    """
    Substitues x in the polynomial represented by the list of coeffs
    Parameters:
        coeffs - array of polynomial coefficients
                 coeffs[0] + coeffs[1]*x + coeffs[2]*x^2 ...

        x      - a value to substitute
    """
    return sum([coeffs[j] * x ** j for j in range(len(coeffs))])


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
    if b is None:
        b = [1] * (len(a)-1)
    if len(a) == len(b):
        res = 1
    elif len(a) == len(b) + 1:
        res = a[-1]
        a = a[:-1]
    else:
        raise ValueError(f'Expected len(a) == len(b) (or len(b)+1). a:{len(a)} b:{len(b)}')


    for a_val, b_val in zip(reversed(a), reversed(b)):
        res = a_val + b_val / res

    return res



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
    assert (math.e == e), f'Expected {e} == {math.e}'
    
    # test that we can calculate phi
    phi = (1 + math.sqrt(5)) / 2
    res = continued_fraction([1] * 50)
    assert (phi == res), f'Expected {phi} == {res}'

    print('All algorithms tests passed')