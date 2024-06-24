import simpy
import networkx
import numpy
from numpy import random
import matplotlib
import seaborn
import logging
INTERVAL = 3
NAMENUMBER = 10
USERNUMBER = 10
interests = []
def source(env, interval, nameNumber):
    node = Node()
    interestId = 0
    while True:
        name = random.randint(nameNumber)
        i = Interest(env, name)
        interests.append(i)
        node.receiveInterest(i, interestId)
        t = random.expovariate(1.0 / interval)
        yield env.timeout(t)
        interestId += 1
class Interest(object):
    def __init__(self, env, name):
        self.env = env
        self.arrive = self.env.now
        self.name = name
        self.hitDistance = 0
        self.nodes = [random.randint(USERNUMBER)]

class Node(object):
    def __init__(self):
        self.contentStore = []
        self.pendingInterest = []
        self.forwardingInfoBase = []
        self.leaveCopyDown = 1
        self.cacheHits = 0
        self.total = 0
    def __init__(self, prob):
        self.contentStore = []
        self.pendingInterest = {}
        self.forwardingInfoBase = {}
        self.leaveCopyDown = prob
    def receiveInterest(self, interest, interestId):
        interests[interestId].hitDistance += 1
        interests[interestId].nodes.append(self)
        self.total = self.total + 1
        if interest.name in self.contentStore:
            self.cacheHits = self.cacheHits + 1
            interests[interestId].nodes.pop(len(interests[interestId].nodes)-1)
            yield interests[interestId].nodes[len(interests[interestId].nodes)-1]
        elif interest.name in self.pendingInterest:
            self.pendingInterest[interest.name] = self.pendingInterest[interest.name].add(interest)
        else:
            self.pendingInterest[interest.name] = [interest]
    def receiveData(self, interest):
        self.forwardingInfoBase.pop(interest.name)
        self.pendingInterest.pop(interest.name)


  
env = simpy.Environment()
env.process(source(env, INTERVAL, NAMENUMBER))
env.run(until = 5)
