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
#user-set variables for simulation
PROB = 1
CACHE_SIZE = 20
BANDWIDTH = 100000000
SIGNAL_SPEED = 1500
#when delay is calculated, variance will be added as a random float in the range of (-DELAY_VARIANCE, DELAY_VARIANCE)
DELAY_VARIANCE = 0.005
#data expires at different times depending on the importance
#here the time health information and mission information can be cached in a CS is pre-defined
HI_EXPIRE_TIME = 60
MI_EXPIRE_TIME = 40
class ContentStore(object):
    def __init__(self, env, max, storeList):
        self.env = env
        #currently CS size for all nodes is the same pre-defined constant, but there is a potential for CS stores to have different sizes
        self.maxSize = max
        self.content = storeList
    def searchName(self, interest):
        #CS tries to find data name requested by interest, which also must not be expired
        for d in self.content:
            if interest.dataName == d.name and d.expireTime > self.env.now:
                logging.info("Data: %s found in Content Store", interest.dataName)
                #if found, return true
                return True
        logging.info("Data: %s not found in Content Store", interest.dataName)
        #if not found, return false
        return False
    def cacheData(self, data):
        #first remove all the expired data
        for d in self.content:
            if d.expireTime < self.env.now:
                self.content.remove(d)
                logging.info("%s has expired and has been removed", d.name)
        #CS will cache new data with pre-defined probability PROB
        numb = random.random()
        if numb < PROB:
            cacheStatus[data.name] += 1
            self.content.insert(0, data)
            if len(self.content) > self.maxSize:
                #if there is not enough room in the CS, the last/oldest data will be removed, most likely this will be changed later
                cacheStatus[self.content[len(self.content)-1].name] -= 1
                self.content.pop(len(self.content) - 1)
            logging.info("Cached %s in Content Store", data.name)
        else:
            logging.info("Did not cache %s in Content Store", data.name)
        logging.info("Current state of Content Store: %s", self.content)
    def respondWithData(self, channelId, interest, nodeId):
        #create new data object when responding with data
        data = Data(self.env, interest.id, interest.dataName)
        logging.info("Responding with data: %s to channel %s", interest.dataName, channelId)
        yield self.env.process(channels[channelId].forwardData(data, interest, nodeId))
class PendingInterest(object):
    def __init__(self, env, max):
        self.env = env
        #maxSize hasn't been used yet, but is a consideration for later
        self.maxSize = max
        self.content = {}
    def searchName(self, interest):
        if interest.dataName in self.content:
            logging.info("Data: %s found in Pending Interest Table", interest.dataName)
            #return true if the node has already forwarded an interest for the data requested
            return True
        logging.info("Data: %s not found in Pending Interest Table", interest.dataName)
        #otherwise, return false
        return False
    def addName(self, interest, fromId):
        #pending interest table is a dictionary with data names as keys and more dictionaries as the values
        #internal dictionaries have the interest objects as values and the channels which sent the interests as keys
        self.content[interest.dataName] = {interest: fromId}
        logging.info("Data: %s added to Pending Interest Table", interest.dataName)
    def addInterface(self, interest, fromId):
        #if the requested data has already been requested, the interest will be dropped and the interest object and the channel which sent it will be added to the value for the key matching the data name
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
        #when a request is sent, the FIB will check its content for which channel to forward the interest to based on the data being requested
        yield self.env.process(channels[self.content[interest.dataName]].forwardRequest(interest, nodeId))
class Channel(object):
    def __init__(self, env, id, fromNode, toNode, length, capacity=simpy.core.Infinity):
        self.env = env
        self.id = id
        #each channel connects two nodes
        self.nodes = [fromNode, toNode]
        self.length = length
    def forwardRequest(self, interest, nodeId):
        #delay = propagation delay + transmission delay +/- variance
        delay = self.length/SIGNAL_SPEED + interest.size/BANDWIDTH + random.uniform(-DELAY_VARIANCE, DELAY_VARIANCE)
        #delay must not be less than a minimum value, here 0.01
        if delay < 0.01:
            delay = 0.01
        yield self.env.timeout(delay)
        #the channel determines which node to forward the interest too based on the node it came from
        if self.nodes[0] == nodeId:
            rNodeId = self.nodes[1]
        else:
            rNodeId = self.nodes[0]
        #the node the interest is being forwarded to should not have an id of -1, since these are users which do not have defined nodes in this simulation
        if rNodeId != -1:
            logging.info("Channel %s forwarding request for %s to %s", self.id, interest.dataName, rNodeId)
            #put the interest in the channel's store in the node
            nodes[rNodeId].stores[self.id].put(interest)
    def forwardData(self, d, intrst, nodeId):
        #delay = propagation delay + transmission delay +/- variance
        delay = self.length/SIGNAL_SPEED + d.size/BANDWIDTH + random.uniform(-DELAY_VARIANCE, DELAY_VARIANCE)
        #delay must not be less than a minimum value, here 0.01
        if delay < 0.01:
            delay = 0.01
        yield self.env.timeout(delay)
        #the channel determines which node to forward the data too based on the node it came from
        if self.nodes[0] == nodeId:
            rNodeId = self.nodes[1]
        else:
            rNodeId = self.nodes[0]
        #if the node the data is being forwarded to has an id of -1, the channel is returning the data back to the original user who requested it, and the process is over for the interest
        if rNodeId == -1:
            logging.info("Returning data: %s to user", d.name)
            #calculate and log how long it took to satisfy the interest
            travelTime = self.env.now - intrst.creationTime
            logging.info("...took %s units", travelTime)
        else:
            logging.info("Channel %s forwarding %s to %s", self.id, d.name, rNodeId)
            #put the data in the channel's data store in the node
            nodes[rNodeId].dataStores[self.id].put(d)
class Interest(object):
    def __init__(self, env, id, name):
        self.env = env
        self.id = id
        self.dataName = name
        self.creationTime = self.env.now
        self.size = 1000
class Data(object):
    def __init__(self, env, id, name):
        self.env = env
        self.id = id
        self.name = name
        #size of data packet has an inverse relationship with the specificity of the data
        self.size = 40 + 524280/(name.count('/') + 1)
        self.sendTime = self.env.now
        #the time the data expires is determined based on the type of data
        if "health_info" in self.name:
            self.expireTime = self.sendTime + HI_EXPIRE_TIME
        else:
            self.expireTime = self.sendTime + MI_EXPIRE_TIME
class Node(object):
    def __init__(self, env, id, name, fromChannelIds, csSize, piSize, fbSize, fbData, content):
        self.env = env
        self.id = id
        self.name = name
        #dictionary of stores (simpy resources) for interests and data being forwarded to the node
        self.stores = {}
        self.dataStores = {}
        self.fromChannelIds = fromChannelIds
        #in the stores and dataStores dictionaries, the keys are the channel ids and the values are simpy stores
        for x in fromChannelIds:
            self.stores[x] = simpy.Store(env)
            self.dataStores[x] = simpy.Store(env)
        csContents = content
        #creating instances of the three main parts of each node
        self.contentStore = ContentStore(self.env, csSize, csContents)
        self.pendingInterest = PendingInterest(self.env, piSize)
        self.forwardingBase = ForwardingBase(self.env, fbSize, fbData)
        #cacheHits keeps track of how many times a node finds requested data in its content store, and totalHits keeps track of the total interests which pass through the node
        self.cacheHits = 0
        self.totalHits = 0
    def searchStore(self, storeNum):
        while True:
            #if there is nothing in the store, the function will stop and move on to the next store to search
            intrst = yield self.stores[storeNum].get()
            #if the function keeps running, there is an interest in the store, and it will be sent to the receiveRequest() method
            yield self.env.process(self.receiveRequest(intrst, storeNum))
    def searchDataStore(self, storeNum):
        while True:
            #if the method is searching the store for the last channel in the list, the fromChannelIds list will be shuffled for the next time so as not to be biased towards the first channel
            if storeNum == self.fromChannelIds[len(self.fromChannelIds) - 1]:
                random.shuffle(self.fromChannelIds)
            #if there is nothing in the store, the function will stop and move on to the next store to search
            data = yield self.dataStores[storeNum].get()
            #if the function keeps running, there is a data packet in the store, and it will be sent to the receiveData() method
            yield self.env.process(self.receiveData(data))
    def receiveRequest(self, interest, fromChannelId):
        logging.info("Node %s receiving request for %s", self.id, interest.dataName)
        #the node's total hits goes up by one when receiving an interest, and the hitDistance for that interest also goes up by one
        self.totalHits += 1
        hitDistances[interest.id] += 1
        #below checks if the node is the producer for the data requested, if so, it creates a data packet and sends it back
        if interest.dataName.startswith(self.name):
            logging.info("%s receiving request for %s", self.name, interest.dataName)
            data = Data(self.env, interest.id, interest.dataName)
            logging.info("Responding with data: %s to channel %s", interest.dataName, fromChannelId)
            yield self.env.process(channels[fromChannelId].forwardData(data, interest, self.id))
        #below checks if the requested data is in the node's CS, if so, it creates a data packet and sends it back
        elif self.contentStore.searchName(interest):
            logging.info("Going to respond with data...")
            #cache hits goes up by one
            self.cacheHits += 1
            #a hit occurs on the cache hits timeline graph
            hits.append(1)
            times.append(self.env.now)
            yield self.env.process(self.contentStore.respondWithData(fromChannelId, interest, self.id))
        #if the node has already sent a request for this data (meaning it is already in the PIT), it will add the interface the interest came from to the dictionary entry for the data
        elif self.pendingInterest.searchName(interest):
            self.pendingInterest.addInterface(interest, fromChannelId)
        #otherwise, a new entry will be created in the PIT and the FIB will forward the request
        else:
            self.pendingInterest.addName(interest, fromChannelId)
            yield self.env.process(self.forwardingBase.sendRequest(interest, self.id))
    def receiveData(self, data):
        logging.info("Node %s receiving data: %s", self.id, data.name)
        #the intrsts and channelIds lists hold the important information for forwarding the data
        #entries in these lists with the same index are connected
        intrsts = []
        channelIds = []
        #find the interests and the interfaces associated with data being forwarded in the PIT
        for x in self.pendingInterest.content[data.name]:
            intrsts.append(x)
            channelIds.append(self.pendingInterest.content[data.name][x])
        #remove the entry from the PIT
        self.pendingInterest.removeName(data.name)
        #have the CS (potentially) cache the data
        self.contentStore.cacheData(data)
        #send the data through all the interfaces
        for x in range(0, len(intrsts)):
            yield self.env.process(channels[channelIds[x]].forwardData(data, intrsts[x], self.id))
def interest_arrival(env, channels):
    #interest id starts at 0
    interestId = 0
    #below is an alternate generating pattern which sends requests for the same data through the same interface twice
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
    #below is the looping version of the interest generator
    while True:
        yield env.timeout(random.expovariate(1.0 / 10))  # Interest arrival follows an exponential distribution
        nodeNum = random.randint(0, len(node_names)-1) #generate a random data producer to request data from
        #below the specific data name is specified while creating the interest
        interest = Interest(env, interestId, node_names[nodeNum][random.randint(0, len(node_names[nodeNum])-1)])
        #creating new entry in hit distances list
        hitDistances.append(0)
        logging.info("About to send request for %s", interest.dataName)
        #new interests will be sent through random edge channel
        cIds = [0, 7]
        yield env.process(channels[random.choice(cIds)].forwardRequest(interest, -1))
        interestId += 1
env = simpy.Environment()
#lists for nodes and channels keep track of Node and Channel objects ordered by id
nodes = []
channels = []
#defining data names for each data-producing node
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
#2D list with a list of name lists ordered by node id
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
#hitDistances list keeps track of how many nodes each interest must pass through before a node has the data being requested
#hitDistances indexes match interest ids, each time an interest is created 0 is appended to hitDistances
#each time a node receives a request it adds one to the hitDistances list where the index equals the interest id
hitDistances = []
#cache status keeps track of the number of current caches of each data name across the network
cacheStatus = {}
for r in range(0, len(node_names)):
    for n in node_names[r]:
        cacheStatus[n] = 0
#hits and times list are used for the graph of cache hits
#every time a node is able to satisfy a request with data from its content store it appends 1 to the hits list and the current environment time to the times list
hits = []
times = []
#creating an list of content for the forwarding interest base of each node, ordered by node id
#each node has a dictionary for the content of its forwarding interest base, the keys are data names and the values are the channel indexes to forward requests to
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
#getting results from ndnProjectNetwork file, which are in the form of a dictionary
results = ndnProjectNetwork.graphConfiguration()
H = results["graph"]
#ndnProjectNetwork sends a 2D list of edge channels with each item having the structure of [channel id, node channel is connected to, channel length]
#these are not part of the networkx graph since they are only connected to one node on the edge of the graph
edgeChannels = results["edgeChannels"]
#past variable keeps track of channel ids as they're being added so that edge channel ids can be added at the right index in the channel list
past = -1
for e in H.edges:
    #checking if any edge channels should be added to channels list
    for r in edgeChannels:
        #if edge channel id is between the past id and the current id, the channel will be added to the channels list using the attributes defined in the edgeChannels lists
        if r[0] > past and r[0] < H.edges[e]["id"]:
            channels.append(Channel(env, r[0], -1, r[1], r[2]))
    #channel objects are created and added using the graph edges and their attributes
    channels.append(Channel(env, H.edges[e]["id"], e[0], e[1], H.edges[e]["length"]))
    past = H.edges[e]["id"]
for n in H.nodes:
    #keeps track of channel ids connected to the node, reset each time
    chIds = []
    #checking graph edges for connected channels
    for e in H.edges(n):
        chIds.append(H.edges[e]["id"])
    #checking edge channels
    for r in edgeChannels:
        if r[1] == n:
            chIds.append(r[0])
    logging.info(node_names[n][0])
    #creating the node object and adding
    nodes.append(Node(env, n, node_names[n][0], chIds, CACHE_SIZE, 5, 5, content[n], []))
#creating the queue of environment processes
#interest_arrival generates interests
env.process(interest_arrival(env, channels))
#for each channel conncted to a node object a function is called to search for new entries in the channel's data and interest stores
#channel order in each node is changed each time around
for n in nodes:
    for i in range(0, len(n.fromChannelIds)):
        env.process(n.searchStore(n.fromChannelIds[i]))
        env.process(n.searchDataStore(n.fromChannelIds[i]))
env.run(until=2000)
#calculating the average cache hit ratio
#total calculates the total number of cache hits
#length counts the total number of requests the nodes have received
total = 0
length = 0
for n in nodes:
    if type(n) == Node and n.totalHits != 0:
        total += n.cacheHits/n.totalHits
        length += 1
logging.info("Average cache hit ratio: %s", total/length)
#log the average hit distance
logging.info("Average hit distance: %s", statistics.mean(hitDistances))
#make the graph
center_node = nodes[9]
edge_nodes = set(H) - {center_node}
pos = nx.circular_layout(H.subgraph(edge_nodes))
pos[center_node] = numpy.array([0, 0])
nx.draw(H)
plt.draw()
plt.show()
#make the cache hits timeline graph
plt.scatter(times, hits)
plt.ylabel = "Cache Hits"
plt.xlabel = "Event Time"
plt.show()