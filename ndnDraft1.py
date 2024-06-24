import simpy
import networkx
import numpy
import random
import matplotlib
import seaborn
import logging
import statistics
hitDistances = []
for i in range(1000):
    hitDistances.append(0)
# Step 1: Define the Node class
class Node:
    def __init__(self, env, prob, id):
        self.env = env
        self.pendingInterest = {}
        self.forwardInfo = {}
        self.contentStore = []
        self.prob = prob
        self.id = id
        self.totalHits = 0
        self.hits = 0
    def receive_interest(self, interest):
        self.totalHits += 1
        if type(interest) == Interest:
            hitDistances[interest.id] += 1
        else:
            for x in interest.interestIds:
                hitDistances[x] += 1
        if interest.name in self.contentStore:
            print("Hit")
            self.hits += 1
            if type(interest) == ForwardingInterest:
                for x in interest.fromNodes:
                    if x > 0:
                        yield nodes[x-1].receive_data(interest.name)
        elif interest.name in self.pendingInterest:
            if type(interest) == Interest:
                self.pendingInterest[interest.name].interestIds.append(interest.id)
                self.pendingInterest[interest.name].fromNodes.append(-1)
            else:
                for x in interest.interestIds:
                    self.pendingInterest[interest.name].interestIds.append(x)
                for x in interest.fromNodes:
                    self.pendingInterest[interest.name].fromNodes.append(x)
        else:
            if type(interest) == Interest:
                newFI = ForwardingInterest(env, interest.name, interest.id, self.id)
                self.pendingInterest[interest.name] = newFI
            else:
                self.pendingInterest[interest.name] = interest
            if self.id < 9:
                yield self.env.process(nodes[self.id+1].receive_interest(self.pendingInterest[interest.name]))
        
        
    def receive_data(self, name):
        numb = random.random()
        if numb < self.prob:
            self.contentStore.append(name)
        interest = self.pendingInterest[name]
        for x in interest.fromNodes:
            if x > 0:
                nodes[x-1].receive_data(name)
        self.pendingInterest.pop(name)

class Interest(object):
    def __init__(self, env, name, id):
        self.env = env
        self.arrive = self.env.now
        self.name = name
        self.id = id

class ForwardingInterest(object):
    def __init__(self, env, name, interestId, fromId):
        self.env = env
        self.arrive = self.env.now
        self.name = name
        self.interestIds = [interestId]
        self.fromNodes = [fromId]
    
# Step 2: Define the interest arrival process
def interest_arrival(env, nodes):
    interestId = 0
    while True:
        yield env.timeout(random.expovariate(1.0 / 5))  # Interest arrival follows an exponential distribution
        interest = Interest(env,  random.randint(0, 10), interestId)
        env.process(nodes[0].receive_interest(interest))
        #hitDistances.append(0)
        interestId += 1
# Step 3: Create the simulation environment
env = simpy.Environment()
# Step 4: Create an instance of the Node class
nodes = []
for i in range(10):
    node = Node(env, 1, i)
    cache = []
    for i in range(1):
        rand = random.randint(0, 10)
        while rand in cache:
            rand = random.randint(0, 10)
        cache.append(rand)
        node.contentStore.append(rand)
    nodes.append(node)
    print(len(nodes))
# Step 5: Start the customer arrival process
env.process(interest_arrival(env, nodes))
# Step 6: Run the simulation
env.run(until=2000)
total = 0
count = 0
for x in hitDistances:
    if x > 0:
        total += x
        count += 1
print(total/count)
for x in nodes:
    print(x.hits/x.totalHits)