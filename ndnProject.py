import simpy
import networkx as nx
import numpy
import random
import matplotlib
import matplotlib.pyplot as plt
import seaborn
import logging
import statistics
import pylint
import ndnProjectNetwork
logging.basicConfig(filename = "ndnProject.log", level = logging.INFO)
PROB = 1
CACHE_SIZE = 6
names = ["autonomous_ship", "autonomous_ship/health_info", "autonomous_ship/mission_info", "autonomous_ship/mission_info/mission_description", "autonomous_ship/mission_info/route", "autonomous_ship/mission_info/antennas", "autonomous_ship/mission_info/antennas/antenna1", "autonomous_ship/mission_info/antennas/antenna2", "autonomous_ship/mission_info/antennas/antenna3", "autonomous_ship/details", "autonomous_ship/details/dimensions", "autonomous_ship/details/name", "autonomous_ship/details/model", "autonomous_ship/details/weight", "autonomous_ship/log"]
cacheStatus = {}
G = nx.Graph()
for x in names:
    cacheStatus[x] = 0
hits = []
times = []
class ContentStore(object):
    def __init__(self, env, max, storeList, p):
        self.env = env
        self.maxSize = max
        self.content = storeList
        self.prob = p
    def searchName(self, interest):
        if interest.dataName in self.content:
            logging.info("Data: %s found in Content Store", interest.dataName)
            return True
        logging.info("Data: %s not found in Content Store", interest.dataName)
        return False
    def cacheData(self, dataName):
        numb = random.random()
        if numb < self.prob:
            cacheStatus[dataName] += 1
            self.content.insert(0, dataName)
            if len(self.content) > self.maxSize:
                cacheStatus[self.content[len(self.content)-1]] -= 1
                self.content.pop(len(self.content) - 1)
            logging.info("Cached %s in Content Store", dataName)
        else:
            logging.info("Did not cache %s in Content Store", dataName)
        logging.info("Current state of Content Store: %s", self.content)
    def respondWithData(self, channelId, interest, nodeId):
        data = Data(self.env, interest.id, interest.dataName)
        logging.info("Responding with data: %s to channel %s", interest.dataName, channelId)
        yield self.env.process(channels[channelId].forwardData(data, interest, nodeId))
class PendingInterest(object):
    def __init__(self, env, max):
        self.env = env
        self.maxSize = max
        self.content = {}
    def searchName(self, interest):
        if interest.dataName in self.content:
            logging.info("Data: %s found in Pending Interest Table", interest.dataName)
            return True
        logging.info("Data: %s not found in Pending Interest Table", interest.dataName)
        return False
    def addName(self, interest, fromId):
        self.content[interest.dataName] = {interest: fromId}
        logging.info("Data: %s added to Pending Interest Table", interest.dataName)
    def addInterface(self, interest, fromId):
        self.content[interest.dataName][interest] = fromId
        logging.info("Interface: %s added to %s in Pending Interest Table", fromId, interest.dataName)
    def removeName(self, dataName):
        self.content.pop(dataName)
        logging.info("Data: %s removed from Pending Interest Table", dataName)
class ForwardingBase(object):
    def __init__(self, env, max, interfaces):
        self.env = env
        self.maxSize = max
        self.content = interfaces
    def sendRequest(self, interest, nodeId):
        logging.info("Sending request for %s to Channel: %s", interest.dataName, self.content[interest.dataName])
        yield self.env.process(channels[self.content[interest.dataName]].forwardRequest(interest, nodeId))
class Channel(object):
    def __init__(self, env, id, fromNode, toNode, capacity=simpy.core.Infinity):
        self.env = env
        self.id = id
        self.nodes = [fromNode, toNode]
    def forwardRequest(self, interest, nodeId):
        yield self.env.timeout(5)
        if self.nodes[0] == nodeId:
            rNodeId = self.nodes[1]
        else:
            rNodeId = self.nodes[0]
        if rNodeId != -1:
            logging.info("Channel %s forwarding request for %s to %s", self.id, interest.dataName, rNodeId)
            nodes[rNodeId].stores[self.id].put(interest)
            yield self.env.process(nodes[rNodeId].searchRequest())
    def forwardData(self, d, intrst, nodeId):
        yield self.env.timeout(5)
        if self.nodes[0] == nodeId:
            rNodeId = self.nodes[1]
        else:
            rNodeId = self.nodes[0]
        if rNodeId == -1:
            logging.info("Returning data: %s to user", d.name)
            travelTime = self.env.now - intrst.creationTime
            logging.info("...took %s units", travelTime)
            yield self.env.process(interest_arrival(env, channels))
        else:
            logging.info("Channel %s forwarding %s to %s", self.id, d.name, rNodeId)
            nodes[rNodeId].dataStore.put(d)
            yield self.env.process(nodes[rNodeId].searchData())
class Interest(object):
    def __init__(self, env, id, name):
        self.env = env
        self.id = id
        self.dataName = name
        self.creationTime = self.env.now
        self.hitDistance = 0
class Data(object):
    def __init__(self, env, id, name):
        self.env = env
        self.id = id
        self.name = name
class Node(object):
    def __init__(self, env, id, fromChannelIds, csSize, piSize, fbSize, fbData, p):
        self.env = env
        self.id = id
        self.stores = {}
        self.dataStore = simpy.Store(env)
        self.fromChannelIds = fromChannelIds
        for x in fromChannelIds:
            logging.info("%s, %s", self.id, x)
            self.stores[x] = simpy.Store(env)
        csContents = []
        self.contentStore = ContentStore(self.env, csSize, csContents, p)
        self.pendingInterest = PendingInterest(self.env, piSize)
        self.forwardingBase = ForwardingBase(self.env, fbSize, fbData)
        self.cacheHits = 0
        self.totalHits = 0
    def searchRequest(self):
        while True:
            count = 0
            for x in self.stores:
                logging.info("Node %s CHECKING %s", self.id, x)
                if count == len(self.stores)-1:
                    intrst = yield self.stores[x].get()
                    yield self.env.process(self.receiveRequest(intrst, x))
                else:
                    if len(self.stores[x].items) > 0:
                        intrst = yield self.stores[x].get()
                        yield self.env.process(self.receiveRequest(intrst, x))
                    count += 1
    def searchData(self):
        while True:
            data = yield self.dataStore.get()
            yield self.env.process(self.receiveData(data))
    def receiveRequest(self, interest, fromChannelId):
        logging.info("Node %s receiving request for %s", self.id, interest.dataName)
        self.totalHits += 1
        hitDistances[interest.id] += 1
        if self.contentStore.searchName(interest):
            logging.info("Going to respond with data...")
            self.cacheHits += 1
            hits.append(1)
            times.append(self.env.now)
            yield self.env.process(self.contentStore.respondWithData(fromChannelId, interest, self.id))
        elif self.pendingInterest.searchName(interest):
            self.pendingInterest.addInterface(interest, fromChannelId)
        else:
            self.pendingInterest.addName(interest, fromChannelId)
            yield self.env.process(self.forwardingBase.sendRequest(interest, self.id))
    def receiveData(self, data):
        logging.info("Node %s receiving data: %s", self.id, data.name)
        intrsts = []
        channelIds = []
        for x in self.pendingInterest.content[data.name]:
            intrsts.append(x)
            channelIds.append(self.pendingInterest.content[data.name][x])
        self.pendingInterest.removeName(data.name)
        self.contentStore.cacheData(data.name)
        for x in range(len(intrsts)):
            yield self.env.process(channels[channelIds[x]].forwardData(data, intrsts[x], self.id))
        yield self.env.process(interest_arrival(env, channels))
class DataProducer(object):
    def __init__(self, env, id, name, fromChannelIds, content):
        self.env = env
        self.id = id
        self.name = name
        self.fromChannelIds = fromChannelIds
        self.content = content
        self.stores = {}
        for x in fromChannelIds:
            self.stores[x] = simpy.Store(env)
    def searchRequest(self):
        while True:
            count = 0
            for x in self.stores:
                logging.info("Node %s CHECKING %s", self.id, x)
                if count == len(self.stores)-1:
                    logging.info("LAST")
                    intrst = yield self.stores[x].get()
                    yield self.env.process(self.receiveRequest(intrst, x))
                else:
                    if len(self.stores[x].items) > 0:
                        intrst = yield self.stores[x].get()
                        yield self.env.process(self.receiveRequest(intrst, x))
                    count += 1
    def receiveRequest(self, interest, fromChannelId):
        logging.info("Data producer has received request")
        data = Data(self.env, interest.id, interest.dataName)
        hitDistances[interest.id] += 1
        yield self.env.process(channels[fromChannelId].forwardData(data, interest, self.id))
    
def interest_arrival(env, channels):
    interestId = 0
    # name = names[random.randint(0, len(names))-1]
    # interest = Interest(env, interestId, name)
    # hitDistances.append(0)
    # logging.info("About to send request for %s", interest.dataName)
    # yield env.process(channels[0].forwardRequest(interest, -1))
    # yield env.timeout(20)
    # interestId = 1
    # interest = Interest(env, interestId, name)
    # hitDistances.append(0)
    # logging.info("About to send request for %s", interest.dataName)
    # yield env.process(channels[0].forwardRequest(interest, -1))
    while True:
        yield env.timeout(random.expovariate(1.0 / 5))  # Interest arrival follows an exponential distribution
        interest = Interest(env, interestId, names[random.randint(0, len(names))-1])
        hitDistances.append(0)
        logging.info("About to send request for %s", interest.dataName)
        cIds = [0, 4, 8]
        yield env.process(channels[random.choice(cIds)].forwardRequest(interest, -1))
        interestId += 1
env = simpy.Environment()
hitDistances = []
nodes = []
channels = []
content = []
content1 = {}
for n in names:
    content1[n] = 1
content.append(content1)
content2 = {}
for n in names:
    content2[n] = 2
content.append(content2)
content3 = {}
for n in names:
    content3[n] = 3
content.append(content3)
content4 = {}
for n in names:
    content4[n] = 5
content.append(content4)
content5 = {}
for n in names:
    content5[n] = 6
content.append(content5)
content6 = {}
for n in names:
    content6[n] = 7
content.append(content6)
content7 = {}
for n in names:
    content7[n] = 9
content.append(content7)
content8 = {}
for n in names:
    content8[n] = 10
content.append(content8)
content9 = {}
for n in names:
    content9[n] = 11
content.append(content9)
results = ndnProjectNetwork.graphConfiguration()
H = results["graph"]
edgeChannels = results["edgeChannels"]
dataProducers = results["dataProducers"]
past = -1
for e in H.edges:
    for r in edgeChannels:
        if r[0] > past and r[0] < H.edges[e]["object"]:
            channels.append(Channel(env, r[0], -1, r[1]))
    channels.append(Channel(env, H.edges[e]["object"], e[0], e[1]))
    past = H.edges[e]["object"]
for n in H.nodes:
    chIds = []
    for e in H.edges(n):
        chIds.append(H.edges[e]["object"])
    for r in edgeChannels:
        if r[1] == n:
            chIds.append(r[0])
    if n in dataProducers:
        nodes.append(DataProducer(env, n, "Ship", chIds, names))
        break
    nodes.append(Node(env, n, chIds, CACHE_SIZE, 5, 5, content[n], PROB))
for n in nodes:
    logging.info(n.fromChannelIds)
for c in channels:
    logging.info(c.nodes)
env.process(interest_arrival(env, channels))
for n in nodes:
    env.process(n.searchRequest())
    if type(n) == Node:
        env.process(n.searchData())
env.process(nodes[0].searchRequest())
env.run(until=4000)
total = 0
length = 0
for n in nodes:
    if type(n) == Node and n.totalHits != 0:
        total += n.cacheHits/n.totalHits
        length += 1
logging.info("Average cache hit ratio: %s", total/length)
logging.info("Average hit distance: %s", statistics.mean(hitDistances))
center_node = nodes[9]
edge_nodes = set(H) - {center_node}
pos = nx.circular_layout(H.subgraph(edge_nodes))
pos[center_node] = numpy.array([0, 0])
nx.draw(H)
plt.draw()
plt.show()
plt.scatter(times, hits)
plt.ylabel = "Cache Hits"
plt.xlabel = "Event Time"
plt.show()