import math
import algorithms
from mpmath import mpf

# just an empty object we can hang properties off of dynamically
class Config(object): pass

phi = mpf( (1 + math.sqrt(5)) / 2)

hashtable_filename = "hashtable.bin"

lhs = Config()

# Be sure each constant in the list is wrapped in mpf()
lhs.constants = [mpf(math.e), mpf(phi)]
lhs.algorithm = algorithms.rational_function 

# This range simply searches for the constant
lhs.a_range   = [[ [0,1], [1,2], [0,1] ]]
lhs.b_range   = [[ [1,2], [0,1], [0,1] ]]


rhs = Config()
rhs.algorithm = algorithms.continued_fraction

# range(i, j) polynomial f(x) goes from i to j - 1
rhs.polynomial_range = range(0, 201)

#
#                    C   +  Bx   + Ax^2
#
rhs.a_range = [[ [-2,2], [-2,2], [-2,2] ]]
rhs.b_range = [[ [-2,2], [-2,2], [-2,2] ]]

# rhs.a_range = [[ [-4,4], [-4,4], [-4,4] ]]
# rhs.b_range = [[ [-4,4], [-4,4], [-4,4] ]]

# rhs.a_range = [[ [-10,10], [-10,10], [-10,10] ]]
# rhs.b_range = [[ [-10,10], [-10,10], [-10,10] ]]

# continued fraction for e
# rhs.a_range = [[ [3,4], [1,2], [0,1] ]] 
# rhs.b_range = [[ [0,1], [-1,0], [0,1] ]]

# continued fraction for phi
# rhs.a_range = [[ [1,2], [0,1], [0,1] ]] 
# rhs.b_range = [[ [1,2], [0,1], [0,1] ]]

