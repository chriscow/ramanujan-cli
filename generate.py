import config
from datetime import datetime
from mpmath import mpf
from algorithms import coefficients, continued_fraction, solve_polynomial
from data import DecimalHashTable


def iterate_coefficients():
    # pa and pb are just aliases so the code is shorter
    pa = config.a_coefficient_ranges
    pb = config.b_coefficient_ranges

    # coefficients() returns an iterator that covers all coefficient possibilities
    a_range = coefficients(pa)
    b_range = coefficients(pb)

    for a_coeff in a_range:
        for b_coeff in b_range:    
            yield a_coeff[0], b_coeff[0]


if "__main__" == __name__:

    ht = DecimalHashTable(8)

    # pa and pb are just aliases so the code is shorter
    pa = config.a_coefficient_ranges
    pb = config.b_coefficient_ranges
    
    start = datetime.now()
    fraction_depth = 200

    for a_coeff, b_coeff in iterate_coefficients():

        # for each coefficient combination, solve the polynomial for x 0 => depth
        a_poly = [solve_polynomial(a_coeff, x) for x in range(0, fraction_depth)]
        b_poly = [solve_polynomial(b_coeff, x) for x in range(0, fraction_depth)]

        # calculate the continued fraction from the polynomial values 
        result = continued_fraction(a_poly, b_poly)
        
        # store the fraction result in the hashtable along with the
        # coefficients that generated it
        ht.setdefault(abs(mpf(result)),[]).append((pa,pb))

    stop = datetime.now()
    print(f'Finished in {(stop-start).total_seconds()}')
