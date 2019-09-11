import mpmath
from mpmath import mpf, mpc

def identity(x):
    return x

# Every function in this file needs a type_id added to it. The type_id values
# can never change.
#
# This is the value stored in the hashtable to identify which function
# was used for the result.
identity.type_id=0


def inverse(x):
    if x == 0:
        return mpmath.mpf('inf')
    else:
        return 1 / x

inverse.type_id=1


def squared(x):
    return x ** 2

squared.type_id=2


def cubed(x):
    return x ** 3

cubed.type_id=3


def quartic(x):
    return x ** 4

quartic.type_id=4


def quintic(x):
    return x ** 5

quintic.type_id = 5


def sextic(x):
    return x ** 6

sextic.type_id = 6


def heptic(x):
    return x ** 7

heptic.type_id = 7


def squared_inverse(x):
    return inverse(x**2)

squared_inverse.type_id = 8


def cubic_inverse(x):
    return inverse(x**3)

cubic_inverse.type_id = 9


def quartic_inverse(x):
    return inverse(x**4)

quartic_inverse.type_id = 10


def quintic_inverse(x):
    return inverse(x**5)

quintic_inverse.type_id = 11


def sextic_inverse(x):
    return inverse(x**6)

sextic_inverse.type_id = 12


def heptic_inverse(x):
    return inverse(x**7)

heptic_inverse.type_id = 13


def sqrt(x):
    if isinstance(x, mpf) and x < 0:
        return mpmath.mpf('NaN')
    else:
        return mpmath.sqrt(x)

sqrt.type_id = 14


def sqrt_inverse(x):
    return inverse(sqrt(x))

sqrt_inverse.type_id = 15


def sin(x):
    return mpmath.sin(x)

sin.type_id = 16


def cos(x):
    return mpmath.cos(x)

cos.type_id = 17


def tan(x):
    return mpmath.tan(x)

tan.type_id = 18


def cot(x):
    if x == 0:
        return mpmath.mpf('NaN')
    else:
        return mpmath.cot(x)

cot.type_id = 19


def exp(x):
    return mpmath.exp(x)

exp.type_id = 20


def ln(x):
    return mpmath.ln(x)

ln.type_id = 21


def sin_inverse(x):
    return inverse(sin(x))

sin_inverse.type_id = 22


def cos_inverse(x):
    return inverse(cos(x))

cos_inverse.type_id = 23


def tan_inverse(x):
    return inverse(tan(x))

tan_inverse.type_id = 24


def cot_inverse(x):
    return inverse(cot(x))

cot_inverse.type_id = 25


def exp_inverse(x):
    return inverse(exp(x))

exp_inverse.type_id = 26


def ln_inverse(x):
    return inverse(ln(x))

ln_inverse.type_id = 27

