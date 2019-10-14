import mpmath
from mpmath import mpf, mpc

import algorithms

# set the decimal precision (not hashtable precision)
mpmath.mp.dps = 15  # 15 decimal places is the default for mpmath anyway but you can change it here


# just an empty object we can hang properties off of dynamically
class Config(object): pass

hash_precision = 8

min_workqueue_size = 10
max_workqueue_size = 100 # maximum jobs in flight per worker before we wait for them to finish
job_result_ttl=60 * 30 # longest amount of time before you check on a job's (complete) status


# Python list of interesting constants.
# Be sure each constant in the list is wrapped in quotes to preserve precision
constants = [ 'mpmath.sqrt(3)', 'mpmath.sqrt(5)', 'mpmath.sqrt(7)',
'mpmath.phi', 
'mpmath.e',
'mpmath.euler', 
'mpmath.degree', 

# https://en.wikipedia.org/wiki/Catalan%27s_constant
'mpmath.catalan',

# Apery's constant happens to be ζ(3) 
# https://en.wikipedia.org/wiki/Ap%C3%A9ry%27s_constant
'mpmath.apery', 

# https://en.wikipedia.org/wiki/Khinchin%27s_constant
# In number theory, Aleksandr Yakovlevich Khinchin proved that for almost all 
# real numbers x, coefficients a sub-i of the continued fraction expansion of x 
# have a finite geometric mean that is independent of the value of x and is 
# known as Khinchin's constant.
#
# That is, for:
#                 1
#    x = a0 + -----------
#                     1
#             a1 + ---------
#                         1
#                  a2 + ---------
#                     [ ... ]
# it is almost always true that
#
# lim(a1,a2, ... an)^(1/n) = mpmath.khinchin
# n -> ∞
'mpmath.khinchin', 

# https://en.wikipedia.org/wiki/Glaisher%E2%80%93Kinkelin_constant
# Glaisher–Kinkelin constant is an important constant which appears in many expressions for the 
# derivative of the Riemann zeta function. It has a numerical value of 
# approximately 1.2824271291.
'mpmath.glaisher', 

# https://en.wikipedia.org/wiki/Meissel%E2%80%93Mertens_constant
# prime reciprocal constant
# defined as the limiting difference between the harmonic series summed only 
# over the primes and the natural logarithm of the natural logarithm
'mpmath.mertens', 

# https://en.wikipedia.org/wiki/Twin_prime#First_Hardy%E2%80%93Littlewood_conjecture
'mpmath.twinprime',

# First Riemann zeta zeros
'14.134725141734693790457251983562470270784257115699243175685567460149963429809256764949010393171561012779202971548797436766142691469882254582505363239447137780413381237205970549621955865860200555566725836010773700205410982661507542780517442591306254481978651072304938725629738321577420395215725674809332140034990468034346267314420920377385487141378317356396995365428113079680531491688529067820822980492643386667346233200787587617920056048680543568014444246510655975686659032286865105448594443206240727270320942745222130487487209241238514183514605427901524478338354254533440044879368067616973008190007313938549837362150130451672696838920039176285123212854220523969133425832275335164060169763527563758969537674920336127209259991730427075683087951184453489180086300826483125169112710682910523759617977431815170713545316775495153828937849036474709727019948485532209253574357909226125247736595518016975233461213977316005354125926747455725877801472609830808978600712532087509395997966660675378381214891908864977277554420656532052405',
'21.022039638771554992628479593896902777334340524902781754629520403587598586068890799713658514180151419533725473642475891383865068603731321262118821624375741669256544711844071194031306725646227792614887337435552059147397132822662470789076753814440726466841906077127569834054514028439923222536788268236111289270057585653273158866604214000907115108009006972002799871101758475196322164968659005748112479386916383518372342780734490239101038504575641215958399921001621834669113158721748057170315793581797724963272407699221125663441561823605180476714422714655559673781247765004555840908644291697757046381655177496445249876742370366456577704837992029270664315837893238009151146858070430828784147861992007607760477484140782738907003895760433245127827863720909303797251823709180804230666738343799022825158287887617612661871382967858745623765006662420780814517636976391374340593412797549697276850306200263121273830462939302565414382374433344022024800453343883072838731260230654753483786801182789317520010690056016544152811050970637593228',
'25.010857580145688763213790992562821818659549672557996672496542006745092098441644277840238224558062440750471046149055778378299851522730801188133933582671689587225169810438735512928493727191994622975912675478696628856807735070039957723114023284276873669399873219586487752250099192453474976208576612334599735443558367531381265997764529037448496994791137897722066199307189972322549732271630051591619212797740876600067291498308127930667027350849516001984670542469491796695225514179319665391273414521673160233737754489414641711937848957499751411065856287969007670986282721864953729632392584034913871430489335889461149586242390368556175189359878735685683089271444468756375337019130417377142535868018531867896375326868632660719766920532953347850670798287711867494428143972542551653196797799127226844589692794085995072279605136120213696806476533976269691774251249095257214003855886494422730332216278403670865759210329078986615602048427519273514192759701784916608441107482155912831074931422640278339513428773126644105168571016344289902',
'30.424876125859513210311897530584091320181560023715440180962146036993329389333277920290584293902089110630991711527395499117633226671186319391807225956714243341155906854681365580724173498447249593190408116323150197023484841630221400985620739718392018133021868063298225719752250023746856136974712496442622977924504057490671534572788651506516083246879706281778104577772258789192373862900112760309735680890492530064612892727530919447902003589389819427495511323917384271638108400499211198006924387188729695970002910005477427068908168462593483850770799656037339265916317859005583905968157207307962526205494009595158923181955070031204385472912847073737931700052460469858203860095171051337905912538151203525649548068653947457306442869841989012474276200924947673637581472033220866876014572657774071196727343504792345035161879811455794448693261212914417916583251901867849867644777729648215979712565041026341481014213352401333833266814485615449144877122011828407076516476221131280807023768331017097022722833154052850963731871619582513781'
]

lhs = {
    "algorithms": [algorithms.rational_function],

    # Take the left-side algorithm result and run it through all the functions in postproc.py
    # and save those values too.  Takes much longer though
    "run_postproc": False,

    # If the algorithm (or postproc functions) results in any of these values, 
    # don't store it
    "black_list": set([-2, -1, 0, 1, 2]),

    "a_sequences": [
        {
        "generator": algorithms.polynomial_sequence,
        "arguments": [ [[ [0,1], [1,2], [0,1] ]], None ]
        }
    ],

    "b_sequences": [
        {
        "generator": algorithms.polynomial_sequence,
        "arguments": [ [[ [1,2], [0,1], [0,1] ]], None ]
        }
    ]
}

#
# The ranges below define the ranges of the coefficients in reverse order.
#
#                    C   +  Bx   + Ax^2
#   [[ [C_start, C_end], [B_start, B_end], [A_start, A_end] ]]
#
# where then END values are non-inclusive.
#

# This range simply searches for the constant
# lhs.a_range   = [[ [0,1], [1,2], [0,1] ]]
# lhs.b_range   = [[ [1,2], [0,1], [0,1] ]]

#                     
# Finds  e / (e - 2)  3.784422382354666325454672914929687976837158203125
# lhs.a_range   = [[ [0,1], [1,2], [0,1] ]]       # numerator
# lhs.b_range   = [[ [-2,-1], [1,2], [0,1] ]]     # denominator

# Finds 1 / (e - 2)
# lhs.a_range   = [[ [1,2], [0,1], [0,1] ]]
# lhs.b_range   = [[ [-2,-1], [1,2], [0,1] ]]


# lhs.a_range   = [[ [-2,2], [-2,2], [-2,2] ]]
# lhs.b_range   = [[ [-2,2], [-2,2], [-2,2] ]]

# Slow, especially with postproc fn()'s called
# lhs.a_range = [[ [-4,4], [-4,4], [-4,4] ]]
# lhs.b_range = [[ [-4,4], [-4,4], [-4,4] ]]

# don't do this one yet ...  
#       ____
#     ,'   Y`.
#    /        \
#    \ ()  () /
#     `. /\ ,'
# 8====| "" |====8
#      `LLLU'
# lhs.a_range = [[ [-10,10], [-10,10], [-10,10] ]]
# lhs.b_range = [[ [-10,10], [-10,10], [-10,10] ]]

# lhs.a_generator = Config()
# lhs.b_generator = Config()
# lhs.a_generator.algorithm = algorithms.polynomial_sequence
# lhs.a_generator.arguments = (lhs.a_range, constants)
# lhs.b_generator.algorithm = algorithms.polynomial_sequence
# lhs.b_generator.arguments = (lhs.b_range, constants)

# # # # # #
#
# Right Hand Side
#
# # # # # #

rhs = {
    "algorithms": [algorithms.nested_radical, algorithms.continued_fraction],

    # Take the left-side algorithm result and run it through all the functions in postproc.py
    # and save those values too.  Takes much longer though
    "run_postproc": True,

    # If the algorithm (or postproc functions) results in any of these values, 
    # don't store it
    "black_list": set([-2, -1, 0, 1, 2]),

    "a_sequences": [  # Sequence lengths all need to match (b can be + 1 in length)
        {
            "generator": algorithms.integer_sequence, # integer sequence of 201 digits:
            "arguments": ( [1,2], 2, 100, [1], 1 )    # 2 digit repeating 100x sequence plus a single
        },
        {
            "generator": algorithms.polynomial_sequence,
            "arguments": ([[ [1,4], [0,2], [0,1] ]], range(0, 201))
        }
    ],

    "b_sequences": [
        {
            "generator": algorithms.polynomial_sequence,
            "arguments": ([[ [0,2], [-1,1], [0,1] ]], range(0, 201))
        },
    ]
}



#
#                    C   +  Bx   + Ax^2
#


# Finds sqrt(3)
    # "a_sequence": {
    #     "generator": algorithms.integer_sequence,
    #     "arguments": ( [1,2], 2, 50, [1], 1 )
    # },

    # "b_sequence": {
    #     "generator": algorithms.polynomial_sequence,
    #     "arguments": ([[ [1,2], [0,1], [0,1] ]], range(0, 101))
    # }

# Generic -2 >> 2 range except little larger range for constant
# in the a_range so that it finds e also.
# rhs.a_range = [[ [-2,4], [-2,2], [-2,2] ]]
# rhs.b_range = [[ [-2,2], [-2,2], [-2,2] ]]

# nested radical finds 3
# rhs.a_range = [[ [1,2], [0,1], [0,1] ]]
# rhs.b_range = [[ [2,3], [1,2], [0,1] ]]


# Slow, especially with postproc fn()'s called
# rhs.b_range = [[ [-4,4], [-4,4], [-4,4] ]]
# rhs.a_range = [[ [-4,4], [-4,4], [-4,4] ]]

# Finds appx e / (e - 2)  = 3.784422382354666325454672914929687976837158203125
#                                           | <-- accurate to this point
# continued fraction finds= 3.784422382354665628753105756959633056747956770630574247182649134166559140923221
# rhs.a_range = [[ [4,5], [1,2], [0,1] ]]
# rhs.b_range = [[ [0,1], [-1,0], [0,1] ]]

# Finds 1 / (e - 2)
# rhs.a_range = [[ [4,5], [1,2], [0,1] ]]
# rhs.b_range = [[ [0,1], [-1,0], [0,1] ]]

# continued fraction for e
# rhs.a_range = [[ [3,4], [1,2], [0,1] ]] 
# rhs.b_range = [[ [0,1], [-1,0], [0,1] ]]

# finds phi for BOTH continued fraction and nested radical
# rhs.a_range = [[ [1,2], [0,1], [0,1] ]] 
# rhs.b_range = [[ [1,2], [0,1], [0,1] ]]

# just enough range to generate BOTH phi and e
# rhs.a_range = [[ [1,4], [0,2], [0,1] ]]
# rhs.b_range = [[ [0,2], [-1,1], [0,1] ]]

# don't do this one yet ...  
#       ____
#     ,'   Y`.
#    /        \
#    \ ()  () /
#     `. /\ ,'
# 8====| "" |====8
#      `LLLU'
# rhs.a_range = [[ [-10,10], [-10,10], [-10,10] ]]
# rhs.b_range = [[ [-10,10], [-10,10], [-10,10] ]]
