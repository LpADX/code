import logging
from functools import partial
from bitstring import BitStream
import math
import arn
from evodevo import Problem, Agent
from utils import *
from utils.bitstrutils import *
from utils.mathlogic import *

log = logging.getLogger(__name__)

def printdotcircuit(circuit, labels=None):
    circuit = circuit.circuit
    s = 'digraph best {\nordering = out;\n'
    for c in circuit:
        s += '%i [label="%s"];\n' % (c[0], c[1])# if not labels
        #else labels[c[1]])
        for inp in c[2]:
            aux = "dir=back"
            if inp < 0:
                aux += ",style=dotted"
            s += '%i -> %i [%s];\n' % (c[0],abs(inp),aux)
    s += '}'
    return s

#TODO: remove! behavior is identical to nnlikefun
def regressionfun(mapped, node_inputs, inputs ):
    if not node_inputs:
        return eval(mapped)
    mainmod = __import__('__main__')
    if mapped in ['if_']:
        return getattr(mainmod, mapped)(*node_inputs)
        #print r
    #    return r
    #else:
    if len(node_inputs) == 1:
        return getattr(mainmod, mapped)(node_inputs[0])
    return reduce(lambda m,n: getattr(mainmod, mapped)(m,n),
                  node_inputs)

def nnlikefun(mapped, node_inputs, inputs):
        mainmod = __import__('__main__')
        if not node_inputs:
            try:
                return eval(mapped)
            except NameError:
                return getattr(mainmod, mapped)(inputs)

        if len(node_inputs) == 1:
            return getattr(mainmod, mapped)(node_inputs[0])
        if mapped not in ReNCoDeProb.funs:
            return getattr(mainmod, mapped)(*node_inputs)
        #print mapped, node_inputs
        return reduce(lambda m,n: getattr(mainmod, mapped)(m,n),
                      node_inputs)


def mergefun(mapped, node_inputs, inputs):
        if not node_inputs:
            return mapped
        else:
            result = mapped + '('
            result += reduce(lambda m, n: m + ',' + n, node_inputs)
            result += ')'
            return result

def defaultnodemap(signature, mappingset):
        if len(mappingset) < 2:
                return mappingset[0]
        index = BitArray(bin=applymajority(
                             signature,
                             int(math.ceil(math.log(len(mappingset),2)))))
        intindex = index.uint
        if intindex >= len(mappingset):
                intindex -= len(mappingset)
        return mappingset[intindex]

def evaluatecircuit(circuit, circuitmap, resultdict, *inputs,**kwargs):
    try:
        nout = kwargs['nout']
    except KeyError:
        nout = 1
    if resultdict == None:
        resultdict = dict()
    for i in range(len(circuit)):
        inputvalues =  [resultdict[abs(v)] for v in circuit[-1-i][2]]
        result = circuitmap(circuit[-1-i][1],
                            inputvalues,
                            inputs)
        resultdict[circuit[-1-i][0]] = result
    if nout == 1:
        return result
    else:
        results = list()
        for i in range(nout):
            if len(circuit) > i:
                results.append(resultdict[circuit[i][0]])
            else:
                results.append(0)
        return results

def buildcircuit(agent, problem, **kwargs):
        """Returns the circuit to be fed into the evaluation function"""
        arn = agent.genotype
        if not arn.promlist:
                return []
        #arn.simulate()
        #orderedps = sorted(arn.proteins, key = lambda x: x[-1], reverse=True)

        graph = arn.ebindings - arn.ibindings
        cleanpairs(graph)
        promlist = [(p[0],
                     _getinputlist(
                                arn.promlist,
                                graph[:,arn.promlist.index(p[0])].tolist()))
                    for p in arn.proteins]

        promlist.sort(key=lambda x: len(x[1]),reverse=True)
        circuit = []
        pdict = dict(zip(arn.promlist,arn.proteins))
        recursivebuild(circuit, problem, pdict, dict(promlist),
                      graph, [promlist[0][0]], [], [])

        return circuit

def recursivebuild(circuit, problem, proteindict, inputdict, graph,
                   pqueue, secondqueue, blacklist):
        if not pqueue:
                if not secondqueue: return circuit
                else:
                        secondqueue.sort(key=lambda x: len(inputdict[x]),
                                         reverse=True)
                        pqueue.append(secondqueue.pop(0))

        next = pqueue.pop(0)
        pnext = proteindict[next]
        blacklist.append(next)
        inputs = []
        for i in inputdict[next]:
                if i in blacklist:
                        if problem.feedback:
                                inputs.append(-i)
                else:
                        inputs.append(i)
        if inputs:
                fun = problem.nodemap_(pnext[4],problem.funs)
                ar = problem.arity[fun]
                if ar > 0 and len(inputs) > ar:
                        del inputs[ar:]
        else:
                fun = problem.nodemap_(pnext[4],problem.terms)

        circuit.append((next, fun , inputs))
        #update input dict if not using feedback
        if not problem.feedback:
                for k,v in inputdict.items():
                        inputdict[k] = filter(
                                lambda i: i not in blacklist, v)

        secondqueue.extend([inp for inp in inputs
                            if  inp not in (pqueue+secondqueue+blacklist)
                            and (inp >= 0)])

        pqueue, secondqueue = _mergequeues(pqueue, secondqueue, inputdict)

        pqueue.sort(key=lambda x: len(inputdict[x]), reverse = True)

        return recursivebuild(circuit, problem, proteindict, inputdict,
                              graph, pqueue,secondqueue, blacklist)

def cleanpairs(matrix):
        s = len(matrix)
        for i in range(s):
                for j in range(i):
                        if matrix[i][j] >= matrix[j][i]:
                                matrix[j][i] = 0
                        else:
                                matrix[i][j] = 0

def _mergequeues(q1, q2,inputdict):
        disjunction = q2[:]
        demoted = []
        for e in q1:
            dependent = False
            if e in [p
                     for pq_el in q1
                     for p in inputdict[pq_el]
                     if pq_el != e]:
                dependent = True
            if e in [p
                     for pq_el in q2
                     for p in inputdict[pq_el]]:
                dependent = True
            if dependent:
                demoted.append(e)
        for e in q2:
            dependent = False
            if e in [p
                     for pq_el in q1
                     for p in inputdict[pq_el]]:
                dependent = True
            if e in [p
                     for pq_el in q2
                     for p in inputdict[pq_el]
                     if pq_el != e]:
                dependent = True

            if dependent:
                disjunction.remove(e)
        for e in demoted: q1.remove(e)
        q2.extend(demoted)
        for e in disjunction: q2.remove(e)
        q1.extend(disjunction)
        return q1,q2

def _getinputlist(promlist, weights):
        """Returns the relevant inputs given the weights."""
        inputs=[]
        pmap = zip(promlist,weights)
        for p,w in pmap:
                if w > 0:
                        inputs.append(p)
        return inputs

def printcircuit(circuit):
        s = ''
        for c in circuit:
                s += "%i [%s]: %s\n" % (c[0], c[1],
                                      reduce(lambda m,n: "%s %s " % (m,n),c[2],
                                             ""))
        return s[:-2]

### Problem base to use with ReNCoDe
class ReNCoDeProb(Problem):
        #TODO: read fun set from config file
        funs = [ 'add_', 'sub_', 'mul_', 'div_']
        terms = [ 'inputs[0]' ]
        labels = {'add_':'+', 'sub_':'-', 'mul_':'*', 'div_':'/',
                  'inputs[0]':'x', 'inputs[1]':'1.0'}
        arity = {}#{'add_':0, 'sub_':0, 'mul_':0, 'div_':0}
        feedback = False
        nout=1
        def __init__(self, evaluate, nodemap = defaultnodemap):
                Problem.__init__(self, evaluate)
                self.nodemap_ = nodemap

#callable phenotype
class P:
    def __init__(self, arnet, circuit, problem, skeleton = regressionfun):
        self.geno = arnet
        self.circuit = circuit
        self.problem = problem
        #memory (disabled by default)
        self.memory = None
        self.funskel = skeleton
        if not problem.feedback:
            self._str = compile(evaluatecircuit(self.circuit, mergefun, self.memory, *problem.terms),
                                '<string>',
                                'eval')

    def getcircuit(self, *args):
        return self.circuit

    def __call__(self, *inputs):
        return evaluatecircuit(self.circuit,self.funskel , self.memory,
                               *inputs, nout = self.problem.nout)

    def __len__(self):
        return len(self.circuit)

    def __eq__(self,other):
        return self.circuit == other.circuit

    def printgraph(self):
        return "GRAPH NOT AVAILABLE"

### Agent model to use with this CoDe module
class ReNCoDeAgent(Agent):
        genotype = None
        phenotype = None
        fitness = None
        def __init__(self, config, problem, gcode = None, parent = None):
                Agent.__init__(self, parent)
                generator = arn.bindparams(config, self.generate)
                if gcode == None:
                        gcode = generator()

                arnet = arn.ARNetwork(gcode,config)
                self.genotype = arnet
                self.phenotype = P(arnet,buildcircuit(self,problem), problem)
                self.problem = problem
                self.fitness = 1e6

        def __str__(self):
                return "### Agent ###\n%s\n%s: %f" % (self.arn,self.phenotype,
                                                      self.fitness)

        def pickled(self):
            return self.print_()

        def print_(self):
            return printdotcircuit(self.phenotype)



class DMAgent(ReNCoDeAgent):
        def __init__(self, config, problem, gcode = None, parent = None):
                self.generate = arn.generatechromo
                ReNCoDeAgent.__init__(self, config, problem, gcode, parent)

class RndAgent(ReNCoDeAgent):
        def __init__(self, config, problem, gcode = None, parent = None):
            self.generate = partial(arn.generatechromo_rnd,
                    genomesize = 32 * pow(2,config.getint('default','initdm')))
            ReNCoDeAgent.__init__(self, config, problem, gcode, parent)

###########################################################################
### Test                                                                ###
###########################################################################

if __name__ == '__main__':
        import ConfigParser
        import random
        from bitstring import BitStream
        from bitstringutils import dm_event
        from arn import ARNetwork
        from evodevo import Problem

        log.setLevel(logging.DEBUG)
        cfg = ConfigParser.ConfigParser()
        cfg.readfp(open('test.cfg'))
        arncfg = ConfigParser.ConfigParser()
        arncfg.readfp(open('arnsim.cfg'))
        proteins=[]
        nump = 0
        while nump < 3:
                genome = BitStream(float=random.random(), length=32)
                for i in range(5):
                        genome = dm_event(genome,
                                          .02)

                arnet = ARNetwork(genome, arncfg)
                nump = len(arnet.promlist)
        for p in arnet.proteins: print p
        prob = Problem(defaultnodemap,regressionfun, None)
        circuit = buildcircuit(arnet, prob,False)
        _printcircuit(circuit)
        print printdotcircuit(circuit, prob.labels)
