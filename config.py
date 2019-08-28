import algorithms
import mpmath
from mpmath import mpf

# set the decimal precision (not hashtable precision)
mpmath.mp.dps = 15  # 15 decimal places is the default for mpmath anyway but you can change it here

# just an empty object we can hang properties off of dynamically
class Config(object): pass

hashtable_filename = "hashtable.bin"
hash_precision = 8

lhs = Config()

# Be sure each constant in the list is wrapped in mpf()
lhs.constants = [mpmath.e, mpmath.phi,
mpf(14.134725141734693790457251983562470270784257115699243175685567460149),
mpf(21.022039638771554992628479593896902777334340524902781754629520403587),
mpf(25.010857580145688763213790992562821818659549672557996672496542006745),
mpf(30.424876125859513210311897530584091320181560023715440180962146036993)]

# Ignore lhs results that equal these values
lhs.skip = [0,1,2]

lhs.algorithm = algorithms.rational_function 

# This range simply searches for the constant
# lhs.a_range   = [[ [0,1], [1,2], [0,1] ]]
# lhs.b_range   = [[ [1,2], [0,1], [0,1] ]]

lhs.a_range   = [[ [-1,2], [-1,2], [-1,2] ]]
lhs.b_range   = [[ [-1,2], [-1,2], [-1,2] ]]


rhs = Config()
rhs.algorithm = algorithms.continued_fraction

# range(i, j) polynomial f(x) goes from i to j - 1
rhs.polynomial_range = range(0, 201)

#
#                    C   +  Bx   + Ax^2
#
rhs.a_range = [[ [-4,4], [-4,4], [-4,4] ]]
rhs.b_range = [[ [-4,4], [-4,4], [-4,4] ]]

# rhs.a_range = [[ [-10,10], [-10,10], [-10,10] ]]
# rhs.b_range = [[ [-10,10], [-10,10], [-10,10] ]]

# continued fraction for e
# rhs.a_range = [[ [3,4], [1,2], [0,1] ]] 
# rhs.b_range = [[ [0,1], [-1,0], [0,1] ]]

# continued fraction for phi
# rhs.a_range = [[ [1,2], [0,1], [0,1] ]] 
# rhs.b_range = [[ [1,2], [0,1], [0,1] ]]

# just enough range to generate BOTH phi and e
# rhs.a_range = [[ [1,4], [0,2], [0,1] ]]
# rhs.b_range = [[ [0,2], [-1,1], [0,1] ]]
