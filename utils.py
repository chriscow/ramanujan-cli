from algorithms import solve_polynomial

# Print iterations progress
def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█'):
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
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = '\r')
    # Print New Line on Complete
    if iteration == total: 
        print()


def printContFrac(result, a_coeff, b_coeff):

    p = solve_polynomial

    print("""
                    {5}
            {1} + ------------
                        {6}
                {2} + ------------
                            {7}              = {0}
                    {3} + -----------
                                {8}
                        {4} + -----------   
                                [...]""".format(result, 
            p(a_coeff, 0), p(a_coeff, 1), p(a_coeff, 2), p(a_coeff, 3),
            p(b_coeff, 1), p(b_coeff, 2), p(b_coeff, 3), p(b_coeff, 4)))