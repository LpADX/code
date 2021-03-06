from code.operators import *
from code.utils import *
from code.utils.mathlogic import *
from code.evodevo import EvoDevoWorkbench
from code.epicode import *
from code.rencode import evaluatecircuit,regressionfun,ReNCoDeProb
import math
import logging
import sys

def drange(start, stop, step):
    r = start
    while r < stop:
        yield r
        r += step

def kozapolynomial(inp):
    return pow(inp,2) - 2*pow(inp,4) + pow(inp,6)

def quarticpolynomial(inp):
    return pow(inp,4) + pow(inp,3) + pow(inp,2) + inp
	
def evaluate(circuit, target, inputs):
    if len(circuit) < 4:
        return 100
    errors = [abs(target(inp) - 
                  evaluatecircuit(circuit, regressionfun,dict(),inp))
              for inp in inputs]
    try:
        sum_ = sum(errors)
    except:
        log.warning('Invalid individual: overflow error...')
        return 100
    
    return 100 if math.isinf(sum_) else sum_


if __name__ == '__main__':
    evalfun = partial(evaluate,
                      target=kozapolynomial,
                      inputs=list(drange(-1,1.1,.1)))
    p = ReNCoDeProb(evalfun)
    edw = EvoDevoWorkbench(sys.argv[1],p,buildcircuit,EpiCoDeAgent)
    edw.run()
    
