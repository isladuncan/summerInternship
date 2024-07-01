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
logging.basicConfig(level = logging.INFO)
PROB = 1
CACHE_SIZE = 6
global dataId
dataId = 0
names = ["books", "books/fiction", "books/nonfiction", "books/fiction/historical-fiction", "books/fiction/fantasy", "books/fiction/adventure", "books/fiction/mystery", "books/nonfiction/encyclopedia", "books/nonfiction/memoir", "books/nonfiction/science", "books/nonfiction/travel", "books/nonfiction/travel/france", "books/nonfiction/science/quantam-mechanics", "books/nonfiction/memoir/i-am-malala", "books/nonfiction/encyclopedia/britannica", "books/fiction/historical-fiction/world-war-2", "books/fiction/fantasy/harry-potter", "books/fiction/adventure/treasure-island", "books/fiction/mystery/nancy-drew"]
cacheStatus = {}
G = nx.Graph()
for x in names:
    cacheStatus[x] = 0
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
    def respondWithData(self, channelId, interest):
        data = Data(self.env, interest.id, interest.dataName)
        logging.info("Responding with data: %s to channel %s", interest.dataName, channelId)
        yield self.env.process(channels[channelId].forwardData(data, interest))
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
    def __init__(self, env, max, interfaces, toChannels):
        self.env = env
        self.maxSize = max
        self.content = interfaces
        self.next = toChannels[0]
    def sendRequest(self, interest):
        logging.info("Sending request for %s to Channel: %s", interest.dataName, self.next)
        yield self.env.process(channels[self.next].forwardRequest(interest))
class Channel(object):
    def __init__(self, env, id, fromNode, toNode, capacity=simpy.core.Infinity):
        self.env = env
        self.id = id
        self.fromNodeId = fromNode
        self.toNodeId = toNode
    def forwardRequest(self, interest):
        if self.toNodeId != -1:
            yield env.timeout(5)
            logging.info("Channel %s forwarding request for %s to %s", self.id, interest.dataName, self.toNodeId)
            nodes[self.toNodeId].stores[self.id].put(interest)

    def forwardData(self, d, intrst):
        yield env.timeout(5)
        if self.fromNodeId == -1:
            logging.info("Returning data: %s to user", d.name)
            travelTime = self.env.now - intrst.creationTime
            logging.info("...took %s units", travelTime)
        else:
            logging.info("Channel %s forwarding %s to %s", self.id, d.name, self.fromNodeId)
            nodes[self.fromNodeId].dataStore.put(d)
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
    def __init__(self, env, id, fromChannelIds, toChannels, csSize, piSize, fbSize, fbData, p):
        self.env = env
        self.id = id
        self.stores = {}
        self.dataStore = simpy.Store(env)
        for x in fromChannelIds:
            self.stores[x] = simpy.Store(env)
        self.toChannelIds = toChannels
        csContents = []
        self.contentStore = ContentStore(self.env, csSize, csContents, p)
        self.pendingInterest = PendingInterest(self.env, piSize)
        self.data = fbData
        for x in self.data:
            self.data[x] = self.toChannelIds[0]
        self.forwardingBase = ForwardingBase(self.env, fbSize, fbData, toChannels)
        self.cacheHits = 0
        self.totalHits = 0
    def searchRequest(self):
        while True:
            for x in self.stores:
                intrst = yield self.stores[x].get()
                yield self.env.process(self.receiveRequest(intrst, x))
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
            yield self.env.process(self.contentStore.respondWithData(fromChannelId, interest))
        elif self.pendingInterest.searchName(interest):
            self.pendingInterest.addInterface(interest, fromChannelId)
        else:
            self.pendingInterest.addName(interest, fromChannelId)
            yield self.env.process(self.forwardingBase.sendRequest(interest))
        yield self.env.process(self.searchRequest())
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
            yield self.env.process(channels[channelIds[x]].forwardData(data, intrsts[x]))
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
            for x in self.stores:
                intrst = yield self.stores[x].get()
                yield self.env.process(self.receiveRequest(intrst, x))
    def receiveRequest(self, interest, fromChannelId):
        logging.info("Data producer has received request")
        data = Data(self.env, interest.id, interest.dataName)
        hitDistances[interest.id] += 1
        yield self.env.process(channels[fromChannelId].forwardData(data, interest))
    
def interest_arrival(env, channels):
    interestId = 0
    # name = names[random.randint(0, len(names))-1]
    # interest = Interest(env, interestId, name)
    # hitDistances.append(0)
    # logging.info("About to send request for %s", interest.dataName)
    # yield env.process(channels[0].forwardRequest(interest))
    # yield env.timeout(2)
    # interestId = 1
    # interest = Interest(env, interestId, name)
    # hitDistances.append(0)
    # logging.info("About to send request for %s", interest.dataName)
    # yield env.process(channels[0].forwardRequest(interest))
    while True:
        yield env.timeout(random.expovariate(1.0 / 5))  # Interest arrival follows an exponential distribution
        interest = Interest(env, interestId, names[random.randint(0, len(names))-1])
        hitDistances.append(0)
        logging.info("About to send request for %s", interest.dataName)
        cIds = [0, 4, 8]
        yield env.process(channels[random.choice(cIds)].forwardRequest(interest))
        interestId += 1
env = simpy.Environment()
hitDistances = []
nodes = []
channels = []
content = []
format = {}
for n in names:
    format[n] = 0
for i in range(0, 10):
    content.append(format)
for i in range(0, 3):
    for x in names:
        content[i][x] = i+1
    print(content)
    nodes.append(Node(env, i, [i], [i+1], CACHE_SIZE, 5, 5, content[i], PROB))
    channels.append(Channel(env, i, i-1, i))
channels.append(Channel(env, 3, 2, 9))
channels.append(Channel(env, 4, -1, 3))
channels.append(Channel(env, 5, 3, 4))
channels.append(Channel(env, 6, 4, 5))
channels.append(Channel(env, 7, 5, 9))
for i in range(3, 6):
    for x in names:
        content[i][x] = i+2
    nodes.append(Node(env, i, [i+1], [i+2], CACHE_SIZE, 5, 5, content[i], PROB))
channels.append(Channel(env, 8, -1, 6))
for i in range(6, 9):
    for x in names:
        content[i][x] = i+3
    nodes.append(Node(env, i, [i+2], [i+3], CACHE_SIZE, 5, 5, content[i], PROB))
    channels.append(Channel(env, i+3, i, i+1))
dProducer = DataProducer(env, 9, "Books", [3, 7, 11], names)
nodes.append(dProducer)
G.add_nodes_from(nodes)
elist = []
for c in channels:
    if c.id != 0 and c.id != 4 and c.id != 8:
        G.add_edge(nodes[c.fromNodeId], nodes[c.toNodeId], object = c)
        elist.append((nodes[c.fromNodeId], nodes[c.toNodeId]))
env.process(interest_arrival(env, channels))
for n in nodes:
    env.process(n.searchRequest())
    if type(n) == Node:
        env.process(n.searchData())
env.run(until=400)
total = 0
length = 0
for n in nodes:
    if type(n) == Node and n.totalHits != 0:
        total += n.cacheHits/n.totalHits
        length += 1
logging.info("Average cache hit ratio: %s", total/length)
logging.info("Average hit distance: %s", statistics.mean(hitDistances))
center_node = nodes[9]
edge_nodes = set(G) - {center_node}
pos = nx.circular_layout(G.subgraph(edge_nodes))
pos[center_node] = numpy.array([0, 0])
# nx.draw_networkx_nodes(G, pos, nodelist=nodes[0:9], node_color="tab:red")
# nx.draw_networkx_nodes(G, pos, nodelist=nodes[9:], node_color="tab:blue")
# fig, ax = plt.subplots()
# nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.5)
# nx.draw_networkx_edges(
#     G,
#     pos=pos,
#     ax=ax,
#     edgelist = elist,
#     arrows=True,
#     arrowstyle="-",
#     min_source_margin=15,
#     min_target_margin=15,
# )
nx.draw(G)
plt.draw()
plt.show()