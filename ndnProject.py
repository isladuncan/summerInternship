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
logging.basicConfig(level = logging.INFO)
PROB = 1
CACHE_SIZE = 6
BANDWIDTH = 100000000
SIGNAL_SPEED = 1500
DELAY_VARIANCE = 0.005
HI_EXPIRE_TIME = 40
MI_EXPIRE_TIME = 20
names = ["autonomous_ship", "autonomous_ship/health_info", "autonomous_ship/mission_info", "autonomous_ship/mission_info/mission_description", "autonomous_ship/mission_info/route", "autonomous_ship/mission_info/antennas", "autonomous_ship/mission_info/antennas/antenna1", "autonomous_ship/mission_info/antennas/antenna2", "autonomous_ship/mission_info/antennas/antenna3", "autonomous_ship/details", "autonomous_ship/details/dimensions", "autonomous_ship/details/name", "autonomous_ship/details/model", "autonomous_ship/details/weight", "autonomous_ship/log"]
uuv_names = ["uuv", "uuv/health_info", "uuv/mission_info", "uuv/mission_info/mission_log", "uuv/mission_info/route", "uuv/mission_info/antennas", "uuv/mission_info/antennas/antenna1", "uuv/mission_info/antennas/antenna2", "uuv/mission_info/antennas/antenna3", "uuv/mission_info/sensors", "uuv/mission_info/sensors/sensor1", "uuv/mission_info/sensors/sensor2", "uuv/mission_info/sensors/sensor3", "uuv/mission_info/location", "uuv/mission_info/depth", "uuv/health_info/log", "uuv/health_info/antenna_conditions/antenna1", "uuv/health_info/antenna_conditions/antenna2", "uuv/health_info/antenna_conditions/antenna3", "uuv/health_info/sensor_conditions/sensor1", "uuv/health_info/sensor_conditions/sensor2", "uuv/health_info/sensor_conditions/sensor3", "uuv/health_info/battery_level"]
uuv1 = ["uuv1", "uuv1/health_info", "uuv1/mission_info", "uuv1/mission_info/mission_log", "uuv1/mission_info/route", "uuv1/mission_info/antennas", "uuv1/mission_info/antennas/antenna1", "uuv1/mission_info/antennas/antenna2", "uuv1/mission_info/antennas/antenna3", "uuv1/mission_info/sensors", "uuv1/mission_info/sensors/sensor1", "uuv1/mission_info/sensors/sensor2", "uuv1/mission_info/sensors/sensor3", "uuv1/mission_info/location", "uuv1/mission_info/depth", "uuv1/health_info/log", "uuv1/health_info/antenna_conditions/antenna1", "uuv1/health_info/antenna_conditions/antenna2", "uuv1/health_info/antenna_conditions/antenna3", "uuv1/health_info/sensor_conditions/sensor1", "uuv1/health_info/sensor_conditions/sensor2", "uuv1/health_info/sensor_conditions/sensor3", "uuv1/health_info/battery_level"]
uuv2 = ["uuv2", "uuv2/health_info", "uuv2/mission_info", "uuv2/mission_info/mission_log", "uuv2/mission_info/route", "uuv2/mission_info/antennas", "uuv2/mission_info/antennas/antenna1", "uuv2/mission_info/antennas/antenna2", "uuv2/mission_info/antennas/antenna3", "uuv2/mission_info/sensors", "uuv2/mission_info/sensors/sensor1", "uuv2/mission_info/sensors/sensor2", "uuv2/mission_info/sensors/sensor3", "uuv2/mission_info/location", "uuv2/mission_info/depth", "uuv2/health_info/log", "uuv2/health_info/antenna_conditions/antenna1", "uuv2/health_info/antenna_conditions/antenna2", "uuv2/health_info/antenna_conditions/antenna3", "uuv2/health_info/sensor_conditions/sensor1", "uuv2/health_info/sensor_conditions/sensor2", "uuv2/health_info/sensor_conditions/sensor3", "uuv2/health_info/battery_level"]
uuv3 = ["uuv3", "uuv3/health_info", "uuv3/mission_info", "uuv3/mission_info/mission_log", "uuv3/mission_info/route", "uuv3/mission_info/antennas", "uuv3/mission_info/antennas/antenna1", "uuv3/mission_info/antennas/antenna2", "uuv3/mission_info/antennas/antenna3", "uuv3/mission_info/sensors", "uuv3/mission_info/sensors/sensor1", "uuv3/mission_info/sensors/sensor2", "uuv3/mission_info/sensors/sensor3", "uuv3/mission_info/location", "uuv3/mission_info/depth", "uuv3/health_info/log", "uuv3/health_info/antenna_conditions/antenna1", "uuv3/health_info/antenna_conditions/antenna2", "uuv3/health_info/antenna_conditions/antenna3", "uuv3/health_info/sensor_conditions/sensor1", "uuv3/health_info/sensor_conditions/sensor2", "uuv3/health_info/sensor_conditions/sensor3", "uuv3/health_info/battery_level"]
uuv4 = ["uuv4", "uuv4/health_info", "uuv4/mission_info", "uuv4/mission_info/mission_log", "uuv4/mission_info/route", "uuv4/mission_info/antennas", "uuv4/mission_info/antennas/antenna1", "uuv4/mission_info/antennas/antenna2", "uuv4/mission_info/antennas/antenna3", "uuv4/mission_info/sensors", "uuv4/mission_info/sensors/sensor1", "uuv4/mission_info/sensors/sensor2", "uuv4/mission_info/sensors/sensor3", "uuv4/mission_info/location", "uuv4/mission_info/depth", "uuv4/health_info/log", "uuv4/health_info/antenna_conditions/antenna1", "uuv4/health_info/antenna_conditions/antenna2", "uuv4/health_info/antenna_conditions/antenna3", "uuv4/health_info/sensor_conditions/sensor1", "uuv4/health_info/sensor_conditions/sensor2", "uuv4/health_info/sensor_conditions/sensor3", "uuv4/health_info/battery_level"]
uuv5 = ["uuv5", "uuv5/health_info", "uuv5/mission_info", "uuv5/mission_info/mission_log", "uuv5/mission_info/route", "uuv5/mission_info/antennas", "uuv5/mission_info/antennas/antenna1", "uuv5/mission_info/antennas/antenna2", "uuv5/mission_info/antennas/antenna3", "uuv5/mission_info/sensors", "uuv5/mission_info/sensors/sensor1", "uuv5/mission_info/sensors/sensor2", "uuv5/mission_info/sensors/sensor3", "uuv5/mission_info/location", "uuv5/mission_info/depth", "uuv5/health_info/log", "uuv5/health_info/antenna_conditions/antenna1", "uuv5/health_info/antenna_conditions/antenna2", "uuv5/health_info/antenna_conditions/antenna3", "uuv5/health_info/sensor_conditions/sensor1", "uuv5/health_info/sensor_conditions/sensor2", "uuv5/health_info/sensor_conditions/sensor3", "uuv5/health_info/battery_level"]
uuv6 = ["uuv6", "uuv6/health_info", "uuv6/mission_info", "uuv6/mission_info/mission_log", "uuv6/mission_info/route", "uuv6/mission_info/antennas", "uuv6/mission_info/antennas/antenna1", "uuv6/mission_info/antennas/antenna2", "uuv6/mission_info/antennas/antenna3", "uuv6/mission_info/sensors", "uuv6/mission_info/sensors/sensor1", "uuv6/mission_info/sensors/sensor2", "uuv6/mission_info/sensors/sensor3", "uuv6/mission_info/location", "uuv6/mission_info/depth", "uuv6/health_info/log", "uuv6/health_info/antenna_conditions/antenna1", "uuv6/health_info/antenna_conditions/antenna2", "uuv6/health_info/antenna_conditions/antenna3", "uuv6/health_info/sensor_conditions/sensor1", "uuv6/health_info/sensor_conditions/sensor2", "uuv6/health_info/sensor_conditions/sensor3", "uuv6/health_info/battery_level"]
usv_names = ["usv", "usv/health_info", "usv/mission_info", "usv/mission_info/mission_log", "usv/mission_info/route", "usv/mission_info/antennas", "usv/mission_info/antennas/antenna1", "usv/mission_info/antennas/antenna2", "usv/mission_info/antennas/antenna3", "usv/mission_info/sensors", "usv/mission_info/sensors/sensor1", "usv/mission_info/sensors/sensor2", "usv/mission_info/sensors/sensor3", "usv/mission_info/location", "usv/health_info/log", "usv/health_info/antenna_conditions/antenna1", "usv/health_info/antenna_conditions/antenna2", "usv/health_info/antenna_conditions/antenna3", "usv/health_info/sensor_conditions/sensor1", "usv/health_info/sensor_conditions/sensor2", "usv/health_info/sensor_conditions/sensor3", "usv/health_info/battery_level"]
usv1 = ["usv1", "usv1/health_info", "usv1/mission_info", "usv1/mission_info/mission_log", "usv1/mission_info/route", "usv1/mission_info/antennas", "usv1/mission_info/antennas/antenna1", "usv1/mission_info/antennas/antenna2", "usv1/mission_info/antennas/antenna3", "usv1/mission_info/sensors", "usv1/mission_info/sensors/sensor1", "usv1/mission_info/sensors/sensor2", "usv1/mission_info/sensors/sensor3", "usv1/mission_info/location", "usv1/health_info/log", "usv1/health_info/antenna_conditions/antenna1", "usv1/health_info/antenna_conditions/antenna2", "usv1/health_info/antenna_conditions/antenna3", "usv1/health_info/sensor_conditions/sensor1", "usv1/health_info/sensor_conditions/sensor2", "usv1/health_info/sensor_conditions/sensor3", "usv1/health_info/battery_level"]
usv2 = ["usv2", "usv2/health_info", "usv2/mission_info", "usv2/mission_info/mission_log", "usv2/mission_info/route", "usv2/mission_info/antennas", "usv2/mission_info/antennas/antenna1", "usv2/mission_info/antennas/antenna2", "usv2/mission_info/antennas/antenna3", "usv2/mission_info/sensors", "usv2/mission_info/sensors/sensor1", "usv2/mission_info/sensors/sensor2", "usv2/mission_info/sensors/sensor3", "usv2/mission_info/location", "usv2/health_info/log", "usv2/health_info/antenna_conditions/antenna1", "usv2/health_info/antenna_conditions/antenna2", "usv2/health_info/antenna_conditions/antenna3", "usv2/health_info/sensor_conditions/sensor1", "usv2/health_info/sensor_conditions/sensor2", "usv2/health_info/sensor_conditions/sensor3", "usv2/health_info/battery_level"]
usv3 = ["usv3", "usv3/health_info", "usv3/mission_info", "usv3/mission_info/mission_log", "usv3/mission_info/route", "usv3/mission_info/antennas", "usv3/mission_info/antennas/antenna1", "usv3/mission_info/antennas/antenna2", "usv3/mission_info/antennas/antenna3", "usv3/mission_info/sensors", "usv3/mission_info/sensors/sensor1", "usv3/mission_info/sensors/sensor2", "usv3/mission_info/sensors/sensor3", "usv3/mission_info/location", "usv3/health_info/log", "usv3/health_info/antenna_conditions/antenna1", "usv3/health_info/antenna_conditions/antenna2", "usv3/health_info/antenna_conditions/antenna3", "usv3/health_info/sensor_conditions/sensor1", "usv3/health_info/sensor_conditions/sensor2", "usv3/health_info/sensor_conditions/sensor3", "usv3/health_info/battery_level"]
usv4 = ["usv4", "usv4/health_info", "usv4/mission_info", "usv4/mission_info/mission_log", "usv4/mission_info/route", "usv4/mission_info/antennas", "usv4/mission_info/antennas/antenna1", "usv4/mission_info/antennas/antenna2", "usv4/mission_info/antennas/antenna3", "usv4/mission_info/sensors", "usv4/mission_info/sensors/sensor1", "usv4/mission_info/sensors/sensor2", "usv4/mission_info/sensors/sensor3", "usv4/mission_info/location", "usv4/health_info/log", "usv4/health_info/antenna_conditions/antenna1", "usv4/health_info/antenna_conditions/antenna2", "usv4/health_info/antenna_conditions/antenna3", "usv4/health_info/sensor_conditions/sensor1", "usv4/health_info/sensor_conditions/sensor2", "usv4/health_info/sensor_conditions/sensor3", "usv4/health_info/battery_level"]
#usv5 = ["usv5", "usv5/health_info", "usv5/mission_info", "usv5/mission_info/mission_log", "usv5/mission_info/route", "usv5/mission_info/antennas", "usv5/mission_info/antennas/antenna1", "usv5/mission_info/antennas/antenna2", "usv5/mission_info/antennas/antenna3", "usv5/mission_info/sensors", "usv5/mission_info/sensors/sensor1", "usv5/mission_info/sensors/sensor2", "usv5/mission_info/sensors/sensor3", "usv5/mission_info/location", "usv5/health_info/log", "usv5/health_info/antenna_conditions/antenna1", "usv5/health_info/antenna_conditions/antenna2", "usv5/health_info/antenna_conditions/antenna3", "usv5/health_info/sensor_conditions/sensor1", "usv5/health_info/sensor_conditions/sensor2", "usv5/health_info/sensor_conditions/sensor3", "usv5/health_info/battery_level"]
node_names = []
node_names.append(usv1)
node_names.append(usv2)
node_names.append(uuv1)
node_names.append(uuv2)
node_names.append(uuv3)
node_names.append(uuv4)
node_names.append(usv3)
node_names.append(usv4)
node_names.append(uuv5)
node_names.append(uuv6)
cacheStatus = {}
G = nx.Graph()
for r in range(0, len(node_names)):
    for n in node_names[r]:
        cacheStatus[n] = 0
hits = []
times = []
class ContentStore(object):
    def __init__(self, env, max, storeList, p):
        self.env = env
        self.maxSize = max
        self.content = storeList
        self.prob = p
    def searchName(self, interest):
        for d in self.content:
            if interest.dataName == d.name and d.expireTime > self.env.now:
                logging.info("Data: %s found in Content Store", interest.dataName)
                return True
        logging.info("Data: %s not found in Content Store", interest.dataName)
        return False
    def cacheData(self, data):
        for d in self.content:
            if d.expireTime < self.env.now:
                self.content.remove(d)
                logging.info("%s has expired and has been removed", d.name)
        numb = random.random()
        if numb < self.prob:
            cacheStatus[data.name] += 1
            self.content.insert(0, data)
            if len(self.content) > self.maxSize:
                cacheStatus[self.content[len(self.content)-1].name] -= 1
                self.content.pop(len(self.content) - 1)
            logging.info("Cached %s in Content Store", data.name)
        else:
            logging.info("Did not cache %s in Content Store", data.name)
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
    def __init__(self, env, id, fromNode, toNode, length, capacity=simpy.core.Infinity):
        self.env = env
        self.id = id
        self.nodes = [fromNode, toNode]
        self.bandwidth = BANDWIDTH
        self.length = length
    def forwardRequest(self, interest, nodeId):
        delay = self.length/SIGNAL_SPEED + interest.size/self.bandwidth + random.uniform(-DELAY_VARIANCE, DELAY_VARIANCE)
        yield self.env.timeout(delay)
        if self.nodes[0] == nodeId:
            rNodeId = self.nodes[1]
        else:
            rNodeId = self.nodes[0]
        if rNodeId != -1:
            logging.info("Channel %s forwarding request for %s to %s", self.id, interest.dataName, rNodeId)
            nodes[rNodeId].storeLengths[self.id] += 1
            nodes[rNodeId].stores[self.id].put(interest)
    def forwardData(self, d, intrst, nodeId):
        delay = self.length/SIGNAL_SPEED + d.size/self.bandwidth + random.uniform(-DELAY_VARIANCE, DELAY_VARIANCE)
        yield self.env.timeout(delay)
        if self.nodes[0] == nodeId:
            rNodeId = self.nodes[1]
        else:
            rNodeId = self.nodes[0]
        if rNodeId == -1:
            logging.info("Returning data: %s to user", d.name)
            travelTime = self.env.now - intrst.creationTime
            logging.info("...took %s units", travelTime)
        else:
            logging.info("Channel %s forwarding %s to %s", self.id, d.name, rNodeId)
            nodes[rNodeId].dataStore.put(d)
class Interest(object):
    def __init__(self, env, id, name):
        self.env = env
        self.id = id
        self.dataName = name
        self.creationTime = self.env.now
        self.hitDistance = 0
        self.size = 1000
class Data(object):
    def __init__(self, env, id, name):
        self.env = env
        self.id = id
        self.name = name
        self.size = 40 + 524280/(name.count('/') + 1)
        self.sendTime = self.env.now
        if "health_info" in self.name:
            self.expireTime = self.sendTime + HI_EXPIRE_TIME
        else:
            self.expireTime = self.sendTime + MI_EXPIRE_TIME
class Node(object):
    def __init__(self, env, id, name, fromChannelIds, csSize, piSize, fbSize, fbData, p, content):
        self.env = env
        self.id = id
        self.name = name
        self.stores = {}
        self.storeLengths = {}
        self.requestStore = simpy.Store(env)
        self.dataStore = simpy.Store(env)
        self.fromChannelIds = fromChannelIds
        for x in fromChannelIds:
            self.stores[x] = simpy.Store(env)
            self.storeLengths[x] = 0
        csContents = content
        self.contentStore = ContentStore(self.env, csSize, csContents, p)
        self.pendingInterest = PendingInterest(self.env, piSize)
        self.forwardingBase = ForwardingBase(self.env, fbSize, fbData)
        self.cacheHits = 0
        self.totalHits = 0
        self.i = -1
    def searchStore(self, storeNum):
        while True:
            intrst = yield self.stores[storeNum].get()
            yield self.env.process(self.receiveRequest(intrst, storeNum))
    def searchData(self):
        while True:
            data = yield self.dataStore.get()
            yield self.env.process(self.receiveData(data))
    def receiveRequest(self, interest, fromChannelId):
        logging.info("Node %s receiving request for %s", self.id, interest.dataName)
        self.totalHits += 1
        hitDistances[interest.id] += 1
        if interest.dataName.startswith(self.name):
            logging.info("%s receiving request for %s", self.name, interest.dataName)
            data = Data(self.env, interest.id, interest.dataName)
            logging.info("Responding with data: %s to channel %s", interest.dataName, fromChannelId)
            yield self.env.process(channels[fromChannelId].forwardData(data, interest, self.id))
        elif self.contentStore.searchName(interest):
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
        self.contentStore.cacheData(data)
        for x in range(len(intrsts)):
            yield self.env.process(channels[channelIds[x]].forwardData(data, intrsts[x], self.id))
def interest_arrival(env, channels):
    interestId = 0
    # name = names[random.randint(0, len(names))-1]
    # interest = Interest(env, interestId, name)
    # hitDistances.append(0)
    # logging.info("About to send request for %s", interest.dataName)
    # yield env.process(channels[0].forwardRequest(interest, -1))
    # yield env.timeout(0.5)
    # interestId = 1
    # interest = Interest(env, interestId, name)
    # hitDistances.append(0)
    # logging.info("About to send request for %s", interest.dataName)
    # yield env.process(channels[0].forwardRequest(interest, -1))
    while True:
        yield env.timeout(random.expovariate(1.0 / 10))  # Interest arrival follows an exponential distribution
        nodeNum = random.randint(0, len(node_names)-1)
        interest = Interest(env, interestId, node_names[nodeNum][random.randint(0, len(node_names[nodeNum])-1)])
        hitDistances.append(0)
        logging.info("About to send request for %s", interest.dataName)
        cIds = [0, 7]
        yield env.process(channels[random.choice(cIds)].forwardRequest(interest, -1))
        interestId += 1
env = simpy.Environment()
hitDistances = []
nodes = []
channels = []
content = []
content1 = {}
for r in range(0, len(node_names)):
    for n in node_names[r]:
        content1[n] = 1
content.append(content1)
content2 = {}
for n in node_names[0]:
    content2[n] = 1
for r in range(2, 10):
    for n in node_names[r]:
        content2[n] = 2
content.append(content2)
content3 = {}
for i in range(0, 2):
    for n in node_names[i]:
        content3[n] = 2
for i in range(3, 10):
    for n in node_names[i]:
        content3[n] = 3
content.append(content3)
content4 = {}
for r in range(0, len(node_names)):
    for n in node_names[r]:
        content4[n] = 4
content.append(content4)
content5 = {}
for n in node_names[3]:
    content5[n] = 4
for r in range(0, 3):
    for n in node_names[r]:
        content5[n] = 5
for r in range(5, 10):
    for n in node_names[r]:
        content5[n] = 5
content.append(content5)
content6 = {}
for r in range(3, 5):
    for n in node_names[r]:
        content6[n] = 5
for r in range(0, 3):
    for n in node_names[r]:
        content6[n] = 6
for r in range(6, 10):
    for n in node_names[r]:
        content6[n] = 6
content.append(content6)
content7 = {}
for r in range(0, len(node_names)):
    for n in node_names[r]:
        content7[n] = 8
content.append(content7)
content8 = {}
for n in node_names[6]:
    content8[n] = 8
for r in range(0, 6):
    for n in node_names[r]:
        content8[n] = 9
for r in range(8, 10):
    for n in node_names[r]:
        content8[n] = 9
content.append(content8)
content9 = {}
for r in range(6, 8):
    for n in node_names[r]:
        content9[n] = 9
for r in range(0, 6):
    for n in node_names[r]:
        content9[n] = 10
for n in node_names[9]:
    content9[n] = 10
content.append(content9)
content10 = {}
for r in range(0, 3):
    for n in node_names[r]:
        content10[n] = 3
for r in range(3, 6):
    for n in node_names[r]:
        content10[n] = 6
for r in range(6, 9):
    for n in node_names[r]:
        content10[n] = 10
content.append(content10)
results = ndnProjectNetwork.graphConfiguration()
H = results["graph"]
edgeChannels = results["edgeChannels"]
dataProducers = results["dataProducers"]
past = -1
for e in H.edges:
    for r in edgeChannels:
        if r[0] > past and r[0] < H.edges[e]["id"]:
            channels.append(Channel(env, r[0], -1, r[1], r[2]))
    channels.append(Channel(env, H.edges[e]["id"], e[0], e[1], H.edges[e]["length"]))
    past = H.edges[e]["id"]
for n in H.nodes:
    chIds = []
    for e in H.edges(n):
        chIds.append(H.edges[e]["id"])
    for r in edgeChannels:
        if r[1] == n:
            chIds.append(r[0])
    logging.info(node_names[n][0])
    nodes.append(Node(env, n, node_names[n][0], chIds, CACHE_SIZE, 5, 5, content[n], PROB, []))
env.process(interest_arrival(env, channels))
for n in nodes:
    for c in n.fromChannelIds:
        env.process(n.searchStore(c))
    env.process(n.searchData())
env.run(until=2000)
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