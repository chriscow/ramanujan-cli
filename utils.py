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
    total = float(total)

    percent = ("0.0") if total == 0 else ("{0:." + str(decimals) + "f}").format(100 * (iteration / total))
    filledLength = 0 if total == 0 else int(length * iteration // total)

    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = '\r')
    # Print New Line on Complete
    if iteration == total: 
        print()


def cont_frac_to_string(result, a_coeff, b_coeff):

    p = solve_polynomial

    return """
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
            p(b_coeff, 1), p(b_coeff, 2), p(b_coeff, 3), p(b_coeff, 4))

def polynomial_to_string(coeff, x):

    res = ['' for i in range(len(coeff))]

    for order in range(len(coeff)):
        res[order] = f'{coeff[order]}'
        if order > 0:
            if order == 1:
                res[order] += f'({x})'
            else:
                res[order] += f'({x})^{order}'
    
    res.reverse()
    return ' + '.join(res)
    