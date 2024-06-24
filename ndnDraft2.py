import simpy
import networkx
import numpy
import random
import matplotlib
from matplotlib import pyplot
import seaborn
import logging
import statistics
NAME_NUMBER = 10
NODE_NUMBER = 10
PROB = 1
EVENT_TIME = 4000
# Step 1: Define the Node class
class Node:
    def __init__(self, env, id):
        self.env = env
        self.pendingInterest = {}
        self.forwardInfo = []
        self.contentStore = []
        self.id = id
        self.totalHits = 0
        self.hits = 0
    def receive_interest(self, name, fromId):
        self.totalHits += 1
        if name in self.contentStore:
            if self.id == 0:
                times.append(env.now)
            self.hits += 1
            if fromId != -1:
                yield self.env.process(nodes[fromId].receive_data(name, self.id))
            else:
                hitDistances.append(self.id+1)
        elif name in self.pendingInterest:
            self.pendingInterest[name].append(fromId)
        else:
            if self.id < NODE_NUMBER-1:
                self.forwardInfo.append(name)
                self.pendingInterest[name] = [fromId]
                yield self.env.process(nodes[self.id+1].receive_interest(name, fromId))

    def receive_data(self, name, endId):
        numb = random.random()
        if numb < PROB:
            self.contentStore.append(name)
            if self.id == 0:
                cacheTimes.append(self.env.now)
                cacheNumber.append(len(self.contentStore))
        interest = self.pendingInterest[name]
        for x in interest.fromNodes:
            if x > 0:
                yield self.env.process(nodes[x-1].receive_data(name, endId))
            else:
                hitDistances.append(endId+1)
        self.pendingInterest.pop(name)

# Step 2: Define the interest arrival process
def interest_arrival(env, nodes):
    interestId = 0
    while True:
        yield env.timeout(random.expovariate(1.0 / 5))  # Interest arrival follows an exponential distribution
        name = random.randint(0, NAME_NUMBER)
        env.process(nodes[0].receive_interest(name, -1))
        interestId += 1
# Step 3: Create the simulation environment
env = simpy.Environment()
# Step 4: Create instances of the Node class
hitDistances = []
nodes = []
times = []
cacheTimes = []
cacheNumber = []
for i in range(NODE_NUMBER):
    node = Node(env, i)
    cache = []
    for i in range(2):
        rand = random.randint(0, NAME_NUMBER)
        while rand in cache:
            rand = random.randint(0, NAME_NUMBER)
        cache.append(rand)
        node.contentStore.append(rand)
    nodes.append(node)
# Step 5: Start the interest arrival process
env.process(interest_arrival(env, nodes))
# Step 6: Run the simulation
env.run(until=EVENT_TIME)
total = 0
count = 1
data = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
increments = []
for i in range(10):
    increments.append((i+1)*EVENT_TIME/10)
print(statistics.mean(hitDistances))
for x in nodes:
    if x.totalHits > 0:
        print(x.hits/x.totalHits)
    else:
        print("No info requests")
for x in times:
    if x <= count*EVENT_TIME/10:
        data[count-1] += 1
    else:
        count += 1
        data[count-1] += 1
pyplot.plot(cacheTimes, cacheNumber)
pyplot.ylabel = "Cache Size"
pyplot.xlabel = "Event Time"
pyplot.show()
# pyplot.plot(increments, data)
# pyplot.ylabel = "Cache Hits"
# pyplot.xlabel = "Event Time"
# pyplot.show()
