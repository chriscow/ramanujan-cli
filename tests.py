import unittest
from mpmath import mpf
from data import *
from algorithms import *

class TestAlgorithms(unittest.TestCase):

    def test_solve_polynomial(self):
        # test solve_polynomial
        # 1 + 2x + 3x^2 where x = 5
        # 1 + 10 + 3 * 25 = 11 + 75 = 86
        res = solve_polynomial([1,2,3], 5)
        self.assertTrue(res == 86)

    def test_coefficients(self):
        coeff_iter = coefficients([[ [-4,4], [-3,3], [-2,2] ]])
        res = sum([solve_polynomial(coeff[0], 7) for coeff in coeff_iter])
        self.assertTrue(res == -5472)

    def test_calc_e(self):
        # test that we can calculate e
        e = continued_fraction(range(3, 50), range(-1, -48, -1))
        self.assertTrue(math.e == e)
    
    def test_calc_phi(self):
        # test that we can calculate phi
        phi = (1 + math.sqrt(5)) / 2
        res = continued_fraction([1] * 50)
        self.assertTrue(phi == res)

    def test_range_calc_e(self):
        a_range    = [[ [3,4], [1,2], [0,1] ]] 
        b_range    = [[ [0,1], [-1,0], [0,1] ]]
        poly_range = config.rhs.polynomial_range
        rhs_algo   = config.rhs.algorithm
        result = self._calc(a_range, b_range, poly_range, rhs_algo)
        self.assertEqual(mpf(math.e), result)

    def test_range_calc_phi(self):
        a_range    = [[ [1,2], [0,1], [0,1] ]]
        b_range    = [[ [1,2], [0,1], [0,1] ]]
        poly_range = config.rhs.polynomial_range
        rhs_algo   = config.rhs.algorithm
        result = self._calc(a_range, b_range, poly_range, rhs_algo)

        phi = mpf( (1 + math.sqrt(5)) / 2)
        self.assertEqual(phi, result)

    def _calc(self, a_range, b_range, poly_range, algo):

        for result, a_coeff, b_coeff in solve(a_range, b_range, poly_range, algo):
            return result

class TestData(unittest.TestCase):

    def test_hashtable(self):
        zeta0 = mpf(14.134725141734693790457251983562470270784257115699243175685567460149963429809256764949010393171561012779202971548797436766142691469882254582505363239447137780413381237205970549621955865860200555566725836010773700205410982661507542780517442591306254481978651072304938725629738321577420395215725674809332140034990468034346267314420920377385487141378317356396995365428113079680531491688529067820822980492643386667346233200787587617920056048680543568014444246510655975686659032286865105448594443206240727270320942745222130487487209241238514183514605427901524478338354254533440044879368067616973008190007313938549837362150130451672696838920039176285123212854220523969133425832275335164060169763527563758969537674920336127209259991730427075683087951184453489180086300826483125169112710682910523759617977431815170713545316775495153828937849036474709727019948485532209253574357909226125247736595518016975233461213977316005354125926747455725877801472609830808978600712532087509395997966660675378381214891908864977277554420656532052405)
        ht = DecimalHashTable(8)
        ht.setdefault(zeta0, []).append(zeta0)
        self.assertFalse(mpf(math.pi) in ht.keys())
        self.assertIsInstance(ht[zeta0], list)
        self.assertIsInstance(ht[zeta0][0], mpf)