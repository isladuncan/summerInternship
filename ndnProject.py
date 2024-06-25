import simpy
import networkx
import numpy
import random
import matplotlib
import seaborn
import logging
import statistics
import pylint
logging.basicConfig(level = logging.DEBUG)
PROB = 0.5
names = ["books", "books/fiction", "books/nonfiction", "books/fiction/historical-fiction", "books/fiction/fantasy", "books/fiction/adventure", "books/fiction/mystery", "books/nonfiction/encyclopedia", "books/nonfiction/memoir", "books/nonfiction/science", "books/nonfiction/travel", "books/nonfiction/travel/france", "books/nonfiction/science/quantam-mechanics", "books/nonfiction/memoir/i-am-malala", "books/nonfiction/encyclopedia/britannica", "books/fiction/historical-fiction/world-war-2", "books/fiction/fantasy/harry-potter", "books/fiction/adventure/treasure-island", "books/fiction/mystery/nancy-drew"]
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
            self.content.insert(0, dataName)
            self.pop(len(self.content) - 1)
            logging.info("Cached %s in Content Store", dataName)
        else:
            logging.info("Did not cache %s in Content Store", dataName)
        logging.info("Current state of Content Store: %s", self.content)
    def respondWithData(self, channelId, interest):
        logging.info("Responding with data: %s to channel %s", interest.dataName, channelId)
        yield self.env.process(channels[channelId].forwardData(interest.dataName, interest))
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
        self.content = {}
        self.interfaceData = interfaces
    def sendRequest(self, interest):
        logging.info("Sending request for %s to Forwarding Interest Base", interest.dataName)
        channels[self.content[interest.dataName]].forwardRequest(interest)
    def addRequest(self, interest, pChannels):
        #just placeholder for now will have to figure out how to decide which channel to go to
        self.content[interest.dataName] = 0
        logging.info("Added request for %s to Forwarding Interest Base", interest.dataName)
    def dropRequest(self, dataName):
        self.content.pop(dataName)
        logging.info("Removed request for %s from Forwarding Interest Base", dataName)
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

    def forwardData(self, dataName, intrst):
        yield env.timeout(5)
        if self.fromNodeId == -1:
            logging.info("Returning data: %s to user", dataName)
            travelTime = self.env.now - intrst.creationTime
            logging.info("...took %s units", travelTime)
        if self.fromNodeId != -1:
            logging.info("Channel %s forwarding %s to %s", self.id, dataName, self.fromNodeId)
            yield self.env.process(nodes[self.toNodeId].receiveData(dataName))
class Interest(object):
    def __init__(self, env, id, name):
        self.env = env
        self.id = id
        self.dataName = name
        self.creationTime = self.env.now
        self.hitDistance = 0
class Node(object):
    def __init__(self, env, id, fromChannelIds, toChannels, csSize, piSize, fbSize, fbData, p):
        self.env = env
        self.id = id
        self.stores = {}
        for x in fromChannelIds:
            self.stores[x] = simpy.Store(env)
        self.toChannelIds = toChannels
        csContents = []
        for i in range(csSize):
            csContents.append(names[i])
        self.contentStore = ContentStore(self.env, csSize, csContents, p)
        self.pendingInterest = PendingInterest(self.env, piSize)
        self.forwardingBase = ForwardingBase(self.env, fbSize, fbData)
        self.cacheHits = 0
        self.totalHits = 0
    def searchInfo(self):
        while True:
            for x in self.stores:
                intrst = yield self.stores[x].get()
                yield self.env.process(self.receiveInfo(intrst, x))
    def receiveInfo(self, interest, fromChannelId):
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
            self.forwardingBase.addRequest(interest, self.toChannelIds)
            self.pendingInterest.addName(interest, fromChannelId)
            self.forwardingBase.sendRequest(interest)
        yield self.env.process(self.searchInfo())
    def receiveData(self, dataName):
        logging.info("Node %s receiving data: %s", self.id, dataName)
        self.forwardingBase.dropRequest(dataName)
        intrsts = []
        channelIds = []
        for x in self.pendingInterest[dataName]:
            intrsts.append(x)
            channelIds.append(self.pendingInterest[dataName][x])
        self.pendingInterest.removeName(dataName)
        self.contentStore.cacheData(dataName)
        for x in range(len(intrsts)):
            yield self.env.process(channels[channelIds[x]].forwardData(dataName, intrsts[x]))
def interest_arrival(env, channels):
    interestId = 0
    while True:
        yield env.timeout(random.expovariate(1.0 / 5))  # Interest arrival follows an exponential distribution
        interest = Interest(env, interestId, names[random.randint(0, len(names))-1])
        hitDistances.append(0)
        logging.info("About to send request for %s", interest.dataName)
        yield env.process(channels[0].forwardRequest(interest))
        interestId += 1
env = simpy.Environment()
hitDistances = []
node = Node(env, 0, [0], [1], 4, 5, 5, [], PROB)
nodes = [node]
channel1 = Channel(env, 0, -1, 0)
channel2 = Channel(env, 1, 0, -1)
channels = [channel1, channel2]
env.process(interest_arrival(env, channels))
for n in nodes:
    env.process(n.searchInfo())
env.run(until=2000)
total = 0
for n in nodes:
    total += n.cacheHits/n.totalHits
logging.info("Average cache hit ratio: %s", total/len(nodes))
logging.info("Average hit distance: %s", statistics.mean(hitDistances))