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
import network
logging.basicConfig(level = logging.INFO)
# User-set variables for simulation.
PROB = 1
CACHE_SIZE = 5
BANDWIDTH = 100000000
SIGNAL_SPEED = 1500
# When delay is calculated, variance will be added as a random float in 
# the range of (-DELAY_VARIANCE, DELAY_VARIANCE).
DELAY_VARIANCE = 0.005
# Data expires at different times depending on the importance.
# Here the time health information and mission information can be cached 
# in a CS is pre-defined.
HI_EXPIRE_TIME = 60
MI_EXPIRE_TIME = 40
SAMPLES = 1
RUN_TIME = 1000


class content_store(object):
    """Represents the Content Store (CS) of a node and its functions.

    Arguments:
    env -- Simpy env in which the simulation takes place
    max -- int representing the max amount of data the CS can hold
    content -- list of data packages the CS holds
    node_id -- int, id of the node the CS belongs to"""

    def __init__(self, env, max, content, node_id):
        self.env = env
        # Currently CS size for all nodes is the same pre-defined constant, but 
        # there is a potential for CS stores to have different sizes.
        self.max_size = max
        self.content = content
        self.node_id = node_id

    def search(self, interest):
        """Checks if the CS already contains the requested data. 
    
        Arguments:
        interest -- Interest object representing the request
        
        Returns: boolean"""

        # CS tries to find data name requested by interest, which also 
        # must not be expired.
        for d in self.content:
            if interest.data_name == d.name and d.expire_time > self.env.now:
                logging.info("Data: %s found in Content Store", interest.data_name)
                # If found, return True.
                return True
        logging.info("Data: %s not found in Content Store", interest.data_name)
        # If not found, return False.
        return False
    
    def cache_data(self, data):
        """Caches/does not cache data using CS management policies.

        Arguments:
        data -- Data object that is travelling through the node"""

        # First remove all the expired data.
        for d in self.content:
            if d.expire_time < self.env.now:
                self.content.remove(d)
                logging.info("%s has expired and has been removed", d.name)
        # CS will cache new data with pre-defined probability PROB.
        numb = random.random()
        if numb < PROB:
            cache_status[data.name] += 1
            self.content.insert(0, data)
            if len(self.content) > self.max_size:
                if self.content[0].name in nodes[self.node_id].data_popularity:
                    min_score = nodes[self.node_id].data_popularity[
                        self.content[0].name]*(self.content[0].expire_time-self.env.now)
                else:
                    min_score = 0
                min_score_index = 0
                for d in self.content:
                    if d.name in nodes[self.node_id].data_popularity:
                        score = nodes[self.node_id].data_popularity[d.name]*(d.expire_time-self.env.now)
                    else:
                        score = 0
                    if score <= min_score:
                        min_score = score
                        min_score_index = self.content.index(d)
                cache_status[self.content[min_score_index].name] -= 1
                self.content.pop(min_score_index)
            logging.info("Cached %s in Content Store", data.name)
        else:
            logging.info("Did not cache %s in Content Store", data.name)
        logging.info("Current state of Content Store: %s", self.content)

    def send_data(self, channel_id, interest):
        """Creates Data object and sends it to the specified channel.
        
        Arguments:
        channel_id -- int, id of the channel which the request came from
        interest -- Interest object representing the request"""

        # Create new data object when responding with data.
        data = Data(self.env, interest.id, interest.data_name)
        logging.info("Responding with data: %s to channel %s", 
                     interest.data_name, channel_id)
        yield self.env.process(channels[channel_id].forward_data(data, interest, self.node_id))


class pending_interest(object):
    """Represents the Pending Interest Table (PIT) of a node 
    and its functions.

    Arguments:
    env -- Simpy env in which the simulation takes place
    max -- int which specifies the max size of the PIT"""

    def __init__(self, env, max):
        self.env = env
        # max_size hasn't been used yet, but is a consideration for later.
        self.max_size = max
        self.content = {}

    def search(self, interest):
        """Checks if the data name requested by the interest is already 
        in the PIT.
        
        Arguments:
        interest -- Interest object representing the request
        
        Returns: boolean"""
    
        if interest.data_name in self.content:
            logging.info("Data: %s found in Pending Interest Table", interest.data_name)
            # Return true if the node has already forwarded an interest for 
            # the data requested.
            return True
        logging.info("Data: %s not found in Pending Interest Table", interest.data_name)
        # Otherwise, return false.
        return False
    
    def add_name(self, interest, fromId):
        """Adds new request to the content of the PIT.
        
        Arguments:
        interest -- Interest object representing the request
        fromId -- int, id for the channel the interest came through"""

        # PIT is a dictionary with data names as keys and 
        # more dictionaries as the values.
        # Internal dictionaries have the interest objects as values and the 
        # channels which sent the interests as keys.
        self.content[interest.data_name] = {interest: fromId}
        logging.info("Data: %s added to Pending Interest Table", interest.data_name)

    def add_interface(self, interest, fromId):
        """Adds Interest object and channel id to an already-existing 
        entry for the data name.

        Arguments:
        interest -- Interest object representing the request
        fromId -- int, the channel id the interest came from"""

        # If the requested data has already been requested, the interest will be 
        # dropped and the interest object and the channel which sent it will be 
        # added to the value for the key matching the data name.
        self.content[interest.data_name][interest] = fromId
        logging.info("Interface: %s added to %s in Pending Interest Table", 
                     fromId, interest.data_name)
        
    def remove(self, data_name):
        """Removes entry in PIT, called when the node receives the data.
        
        Arguments:
        data_name -- String which corresponds to the name of the data"""

        self.content.pop(data_name)
        logging.info("Data: %s removed from Pending Interest Table", data_name)


class forwarding_base(object):
    """Represents the Forwarding Information Base (FIB) of a node and 
    its functions.
    
    Arguments:
    env -- Simpy env in which the simulation takes place
    interfaces -- dictionary matching data names to channel ids
    node_id -- int, id of the node the FIB belongs to"""

    def __init__(self, env, interfaces, node_id):
        self.env = env
        self.content = interfaces
        self.node_id = node_id

    def send_request(self, interest):
        """Sends Interest object to a channel based on the FIB's content.
        
        Arguments:
        interest -- Interest object representing the request"""

        logging.info("Sending request for %s to Channel: %s", interest.data_name, 
                     self.content[interest.data_name])
        # When a request is sent, the FIB will check its content for which 
        # channel to forward the interest to based on the data being requested.
        yield self.env.process(
            channels[self.content[interest.data_name]].forward_interest(interest, self.node_id))
        

class Channel(object):
    """Connecting object between nodes which forwards interests and data.
    
    Arguments:
    env -- Simpy env in which the simulation takes place
    id -- int, the id a channel is assigned to
    nodes -- list containing the ids of the nodes the channel connects
    length -- int representing the length of the channel in meters"""

    def __init__(self, env, id, nodes, length):
        self.env = env
        self.id = id
        self.nodes = nodes
        self.length = length
    
    def forward_interest(self, interest, node_id):
        """Puts the interest object in the store of the receiving node.
        
        Arguments:
        interest -- Interest object representing the request
        node_id -- int, id of the node the interest is coming from"""

        # delay = propagation delay + transmission delay +/- variance
        delay = self.length/SIGNAL_SPEED + interest.size/BANDWIDTH 
        + random.uniform(-DELAY_VARIANCE, DELAY_VARIANCE)
        # delay must not be less than a minimum value, here 0.01.
        if delay < 0.01:
            delay = 0.01
        yield self.env.timeout(delay)
        # The channel determines which node to forward the interest too based on 
        # the node it came from.
        if self.nodes[0] == node_id:
            rnode_id = self.nodes[1]
        else:
            rnode_id = self.nodes[0]
        # The node the interest is being forwarded to should not have an id of 
        # -1, since these are users which do not have defined nodes in 
        # this simulation.
        if rnode_id != -1:
            logging.info("Channel %s forwarding request for %s to %s", self.id, 
                         interest.data_name, rnode_id)
            # Put the interest in the channel's store in the node.
            nodes[rnode_id].stores[self.id].put(interest)

    def forward_data(self, data, interest, node_id):
        """Puts data object in the store of receiving node.
        
        Arguments:
        data -- Data object representing data package
        interest -- Interest object associated with the data name
        node_id -- int, id of the node the interest is coming from"""

        # delay = propagation delay + transmission delay +/- variance
        delay = self.length/SIGNAL_SPEED + data.size/BANDWIDTH 
        + random.uniform(-DELAY_VARIANCE, DELAY_VARIANCE)
        # delay must not be less than a minimum value, here 0.01.
        if delay < 0.01:
            delay = 0.01
        yield self.env.timeout(delay)
        # The channel determines which node to forward the data too based on the 
        # node it came from.
        if self.nodes[0] == node_id:
            rnode_id = self.nodes[1]
        else:
            rnode_id = self.nodes[0]
        # If the node the data is being forwarded to has an id of -1, the 
        # channel is returning the data back to the original user who requested 
        # it, and the process is over for the interest.
        if rnode_id == -1:
            logging.info("Returning data: %s to user", data.name)
            # Calculate and log how long it took to satisfy the interest.
            return_time = self.env.now - interest.creation_time
            logging.info("...took %s units", return_time)
            return_times.append(return_time)
        else:
            logging.info("Channel %s forwarding %s to %s", self.id, data.name, rnode_id)
            # Put the data in the channel's data store in the node.
            nodes[rnode_id].data_stores[self.id].put(data)


class Interest(object):
    """Represents an interest package and its attributes.
    
    Arguments:
    env -- Simpy env in which the simulation takes place
    id -- int, the id the interest is assigned to
    name -- String, name of data interest is requesting"""

    def __init__(self, env, id, name):
        self.env = env
        self.id = id
        self.data_name = name
        self.creation_time = self.env.now
        self.size = 1000


class Data(object):
    """Represents a data package and its attributes.
    
    Arguments:
    env -- Simpy env in which the simulation takes place
    id -- int, the id the data is assigned to
    name -- String, name of data being packaged"""

    def __init__(self, env, id, name):
        self.env = env
        self.id = id
        self.name = name
        # Size of data packet has an inverse relationship with the specificity 
        # of the data.
        self.size = 40 + 524280/(name.count('/') + 1)
        self.send_time = self.env.now
        # The time the data expires is determined based on the type of data
        if "health_info" in self.name:
            self.expire_time = self.send_time + HI_EXPIRE_TIME
        else:
            self.expire_time = self.send_time + MI_EXPIRE_TIME


class Node(object):
    """Represents a node in a network and its processes.
    
    Arguments:
    env -- Simpy env in which the simulation takes place
    id -- int, the id the node is assigned to
    name -- String, the category of data the node produces
    channel_ids -- list containing the ids of the connected channels
    cssize -- int, the max size of the CS
    pisize -- int, the max size of the PIT
    fbdata -- list, the content of the FIB
    cscontent -- list, the starting content of the CS"""

    def __init__(self, env, id, name, channel_ids, cssize, pisize, 
                 fbdata, cscontent):
        self.env = env
        self.id = id
        self.name = name
        # dictionary of stores (simpy resources) for interests and data being 
        # forwarded to the node
        self.stores = {}
        self.data_stores = {}
        self.channel_ids = channel_ids
        # in the stores and data_stores dictionaries, the keys are the channel 
        # ids and the values are simpy stores
        for x in channel_ids:
            self.stores[x] = simpy.Store(env)
            self.data_stores[x] = simpy.Store(env)
        # creating instances of the three main parts of each node
        self.content_store = content_store(self.env, cssize, cscontent, self.id)
        self.pending_interest = pending_interest(self.env, pisize)
        self.forwarding_base = forwarding_base(self.env, fbdata, self.id)
        self.data_popularity = {}
        # cache_hits keeps track of how many times a node finds requested data in 
        # its content store, and total_requests keeps track of the total interests 
        # which pass through the node
        self.cache_hits = 0
        self.total_requests = 0

    def search_interests(self, storeNum):
        """Gets an interest from specified request store, will break if 
        store is empty.
        
        Arguments:
        storeNum: int, the id of the channel associated with the store"""

        while True:
            # If there is nothing in the store, the function will stop and move on 
            # to the next store to search
            intrst = yield self.stores[storeNum].get()
            # if the function keeps running, there is an interest in the store, and 
            # it will be sent to the receive_request() method
            yield self.env.process(self.receive_request(intrst, storeNum))

    def search_data(self, storeNum):
        """Gets a data package from specified data store, will break if 
        store is empty.
        
        Arguments:
        storeNum: int, the id of the channel associated with the store"""

        while True:
            # if the method is searching the store for the last channel in the list, 
            # the channel_ids list will be shuffled for the next time so as not 
            # to be biased towards the first channel
            if storeNum == self.channel_ids[len(self.channel_ids) - 1]:
                random.shuffle(self.channel_ids)
            # if there is nothing in the store, the function will stop and move on 
            # to the next store to search
            data = yield self.data_stores[storeNum].get()
            # if the function keeps running, there is a data packet in the store, 
            # and it will be sent to the receive_data() method
            yield self.env.process(self.receive_data(data))

    def receive_request(self, interest, fromchannel_id):
        """Processes an interest found while searching stores.
        
        Arguments:
        interest -- Interest object representing request
        fromchannel_id -- id of channel interest came from"""

        logging.info("Node %s receiving request for %s", self.id, interest.data_name)
        # the node's total hits goes up by one when receiving an interest, 
        # and the hit distance for that interest also goes up by one
        self.total_requests += 1
        hit_distances[interest.id] += 1
        if interest.data_name in self.data_popularity:
            self.data_popularity[interest.data_name] += 1
        else:
            self.data_popularity[interest.data_name] = 1
        # below checks if the node is the producer for the data requested, 
        # if so, it creates a data packet and sends it back
        if interest.data_name.startswith(self.name):
            logging.info("%s receiving request for %s", self.name, interest.data_name)
            data = Data(self.env, interest.id, interest.data_name)
            logging.info("Responding with data: %s to channel %s", 
                         interest.data_name, fromchannel_id)
            yield self.env.process(channels[fromchannel_id].forward_data(data, interest, 
                                                                       self.id))
        # below checks if the requested data is in the node's CS, if so, it 
        # creates a data packet and sends it back
        elif self.content_store.search(interest):
            logging.info("Going to respond with data...")
            # cache hits goes up by one
            self.cache_hits += 1
            # a hit occurs on the cache hits timeline graph
            hits.append(1)
            times.append(self.env.now)
            yield self.env.process(self.content_store.send_data(fromchannel_id, 
                                                                     interest))
        # if the node has already sent a request for this data (meaning it is 
        # already in the PIT), it will add the interface the interest came from 
        # to the dictionary entry for the data
        elif self.pending_interest.search(interest):
            self.pending_interest.add_interface(interest, fromchannel_id)
        # otherwise, a new entry will be created in the PIT and the FIB will 
        # forward the request
        else:
            self.pending_interest.add_name(interest, fromchannel_id)
            yield self.env.process(self.forwarding_base.send_request(interest))

    def receive_data(self, data):
        """Processes data found while searching data stores.
        
        Arguments:
        data -- Data object representing data package"""

        logging.info("Node %s receiving data: %s", self.id, data.name)
        # the intrsts and channel_ids lists hold the important information for 
        # forwarding the data
        # entries in these lists with the same index are connected
        intrsts = []
        channel_ids = []
        # find the interests and the interfaces associated with data being 
        # forwarded in the PIT
        for x in self.pending_interest.content[data.name]:
            intrsts.append(x)
            channel_ids.append(self.pending_interest.content[data.name][x])
        # remove the entry from the PIT
        self.pending_interest.remove(data.name)
        # have the CS (potentially) cache the data
        self.content_store.cache_data(data)
        # send the data through all the interfaces
        for x in range(0, len(intrsts)):
            yield self.env.process(channels[channel_ids[x]].forward_data(data, 
                                                                       intrsts[x], self.id))
            

def interest_arrival():
    """Creates interest objects and sends them through random 
    edge channels."""

    # interest id starts at 0
    interest_id = 0
    channel_ids = []
    for e in edge_channels:
        channel_ids.append(e["id"])
    # below is an alternate generating pattern which sends requests for the 
    # same data through the same interface twice
    # name = names[random.randint(0, len(names))-1]
    # interest = Interest(env, interest_id, name)
    # hit_distances.append(0)
    # logging.info("About to send request for %s", interest.data_name)
    # yield env.process(channels[0].forward_interest(interest, -1))
    # yield env.timeout(0.5)
    # interest_id = 1
    # interest = Interest(env, interest_id, name)
    # hit_distances.append(0)
    # logging.info("About to send request for %s", interest.data_name)
    # yield env.process(channels[0].forward_interest(interest, -1))
    # below is the looping version of the interest generator
    while True:
        # Interest arrival follows an exponential distribution
        yield env.timeout(random.expovariate(1.0 / 10))  
        if random.random() < 0.3:
            nodenum = 9
        else:
            # generate a random data producer to request data from
            nodenum = random.randint(0, len(node_names)-1) 
        # below the specific data name is specified while creating the interest
        interest = Interest(env, interest_id, node_names[nodenum][random.randint(0, 
                                                                                len(node_names[nodenum])-1)])
        #creating new entry in hit distances list
        hit_distances.append(0)
        logging.info("About to send request for %s", interest.data_name)
        #new interests will be sent through random edge channel
        yield env.process(channels[random.choice(channel_ids)].forward_interest(interest, -1))
        interest_id += 1

env = simpy.Environment()
# lists for nodes and channels keep track of Node and Channel objects 
# ordered by id
nodes = []
channels = []
# defining data names for each data-producing node
uuv1 = ["uuv1", "uuv1/health_info", "uuv1/mission_info", 
        "uuv1/mission_info/mission_log", "uuv1/mission_info/route", 
        "uuv1/mission_info/antennas", "uuv1/mission_info/antennas/antenna1", 
        "uuv1/mission_info/antennas/antenna2", "uuv1/mission_info/antennas/antenna3", 
        "uuv1/mission_info/sensors", "uuv1/mission_info/sensors/sensor1", 
        "uuv1/mission_info/sensors/sensor2", "uuv1/mission_info/sensors/sensor3", 
        "uuv1/mission_info/location", "uuv1/mission_info/depth", 
        "uuv1/health_info/log", "uuv1/health_info/antenna_conditions/antenna1", 
        "uuv1/health_info/antenna_conditions/antenna2", 
        "uuv1/health_info/antenna_conditions/antenna3", 
        "uuv1/health_info/sensor_conditions/sensor1", 
        "uuv1/health_info/sensor_conditions/sensor2", 
        "uuv1/health_info/sensor_conditions/sensor3", "uuv1/health_info/battery_level"]
uuv2 = ["uuv2", "uuv2/health_info", "uuv2/mission_info", 
        "uuv2/mission_info/mission_log", "uuv2/mission_info/route", 
        "uuv2/mission_info/antennas", "uuv2/mission_info/antennas/antenna1", 
        "uuv2/mission_info/antennas/antenna2", "uuv2/mission_info/antennas/antenna3", 
        "uuv2/mission_info/sensors", "uuv2/mission_info/sensors/sensor1", 
        "uuv2/mission_info/sensors/sensor2", "uuv2/mission_info/sensors/sensor3", 
        "uuv2/mission_info/location", "uuv2/mission_info/depth", 
        "uuv2/health_info/log", "uuv2/health_info/antenna_conditions/antenna1", 
        "uuv2/health_info/antenna_conditions/antenna2", 
        "uuv2/health_info/antenna_conditions/antenna3", 
        "uuv2/health_info/sensor_conditions/sensor1", 
        "uuv2/health_info/sensor_conditions/sensor2", 
        "uuv2/health_info/sensor_conditions/sensor3", "uuv2/health_info/battery_level"]
uuv3 = ["uuv3", "uuv3/health_info", "uuv3/mission_info", 
        "uuv3/mission_info/mission_log", "uuv3/mission_info/route", 
        "uuv3/mission_info/antennas", "uuv3/mission_info/antennas/antenna1", 
        "uuv3/mission_info/antennas/antenna2", "uuv3/mission_info/antennas/antenna3", 
        "uuv3/mission_info/sensors", "uuv3/mission_info/sensors/sensor1", 
        "uuv3/mission_info/sensors/sensor2", "uuv3/mission_info/sensors/sensor3", 
        "uuv3/mission_info/location", "uuv3/mission_info/depth", 
        "uuv3/health_info/log", "uuv3/health_info/antenna_conditions/antenna1", 
        "uuv3/health_info/antenna_conditions/antenna2", 
        "uuv3/health_info/antenna_conditions/antenna3", 
        "uuv3/health_info/sensor_conditions/sensor1", 
        "uuv3/health_info/sensor_conditions/sensor2", 
        "uuv3/health_info/sensor_conditions/sensor3", "uuv3/health_info/battery_level"]
uuv4 = ["uuv4", "uuv4/health_info", "uuv4/mission_info", 
        "uuv4/mission_info/mission_log", "uuv4/mission_info/route", 
        "uuv4/mission_info/antennas", "uuv4/mission_info/antennas/antenna1", 
        "uuv4/mission_info/antennas/antenna2", "uuv4/mission_info/antennas/antenna3", 
        "uuv4/mission_info/sensors", "uuv4/mission_info/sensors/sensor1", 
        "uuv4/mission_info/sensors/sensor2", "uuv4/mission_info/sensors/sensor3", 
        "uuv4/mission_info/location", "uuv4/mission_info/depth", 
        "uuv4/health_info/log", "uuv4/health_info/antenna_conditions/antenna1", 
        "uuv4/health_info/antenna_conditions/antenna2", 
        "uuv4/health_info/antenna_conditions/antenna3", 
        "uuv4/health_info/sensor_conditions/sensor1", 
        "uuv4/health_info/sensor_conditions/sensor2", 
        "uuv4/health_info/sensor_conditions/sensor3", "uuv4/health_info/battery_level"]
uuv5 = ["uuv5", "uuv5/health_info", "uuv5/mission_info", 
        "uuv5/mission_info/mission_log", "uuv5/mission_info/route", 
        "uuv5/mission_info/antennas", "uuv5/mission_info/antennas/antenna1", 
        "uuv5/mission_info/antennas/antenna2", "uuv5/mission_info/antennas/antenna3", 
        "uuv5/mission_info/sensors", "uuv5/mission_info/sensors/sensor1", 
        "uuv5/mission_info/sensors/sensor2", "uuv5/mission_info/sensors/sensor3", 
        "uuv5/mission_info/location", "uuv5/mission_info/depth", 
        "uuv5/health_info/log", "uuv5/health_info/antenna_conditions/antenna1", 
        "uuv5/health_info/antenna_conditions/antenna2", 
        "uuv5/health_info/antenna_conditions/antenna3", 
        "uuv5/health_info/sensor_conditions/sensor1", 
        "uuv5/health_info/sensor_conditions/sensor2", 
        "uuv5/health_info/sensor_conditions/sensor3", "uuv5/health_info/battery_level"]
uuv6 = ["uuv6", "uuv6/health_info", "uuv6/mission_info", 
        "uuv6/mission_info/mission_log", "uuv6/mission_info/route", 
        "uuv6/mission_info/antennas", "uuv6/mission_info/antennas/antenna1", 
        "uuv6/mission_info/antennas/antenna2", "uuv6/mission_info/antennas/antenna3", 
        "uuv6/mission_info/sensors", "uuv6/mission_info/sensors/sensor1", 
        "uuv6/mission_info/sensors/sensor2", "uuv6/mission_info/sensors/sensor3", 
        "uuv6/mission_info/location", "uuv6/mission_info/depth", 
        "uuv6/health_info/log", "uuv6/health_info/antenna_conditions/antenna1", 
        "uuv6/health_info/antenna_conditions/antenna2", 
        "uuv6/health_info/antenna_conditions/antenna3", 
        "uuv6/health_info/sensor_conditions/sensor1", 
        "uuv6/health_info/sensor_conditions/sensor2", 
        "uuv6/health_info/sensor_conditions/sensor3", "uuv6/health_info/battery_level"]
usv1 = ["usv1", "usv1/health_info", "usv1/mission_info", 
        "usv1/mission_info/mission_log", "usv1/mission_info/route", 
        "usv1/mission_info/antennas", "usv1/mission_info/antennas/antenna1", 
        "usv1/mission_info/antennas/antenna2", "usv1/mission_info/antennas/antenna3", 
        "usv1/mission_info/sensors", "usv1/mission_info/sensors/sensor1", 
        "usv1/mission_info/sensors/sensor2", "usv1/mission_info/sensors/sensor3", 
        "usv1/mission_info/location", "usv1/health_info/log", 
        "usv1/health_info/antenna_conditions/antenna1", 
        "usv1/health_info/antenna_conditions/antenna2", 
        "usv1/health_info/antenna_conditions/antenna3", 
        "usv1/health_info/sensor_conditions/sensor1", 
        "usv1/health_info/sensor_conditions/sensor2", 
        "usv1/health_info/sensor_conditions/sensor3", "usv1/health_info/battery_level"]
usv2 = ["usv2", "usv2/health_info", "usv2/mission_info", 
        "usv2/mission_info/mission_log", "usv2/mission_info/route", 
        "usv2/mission_info/antennas", "usv2/mission_info/antennas/antenna1", 
        "usv2/mission_info/antennas/antenna2", "usv2/mission_info/antennas/antenna3", 
        "usv2/mission_info/sensors", "usv2/mission_info/sensors/sensor1", 
        "usv2/mission_info/sensors/sensor2", "usv2/mission_info/sensors/sensor3", 
        "usv2/mission_info/location", "usv2/health_info/log", 
        "usv2/health_info/antenna_conditions/antenna1", 
        "usv2/health_info/antenna_conditions/antenna2", 
        "usv2/health_info/antenna_conditions/antenna3", 
        "usv2/health_info/sensor_conditions/sensor1", 
        "usv2/health_info/sensor_conditions/sensor2", 
        "usv2/health_info/sensor_conditions/sensor3", "usv2/health_info/battery_level"]
usv3 = ["usv3", "usv3/health_info", "usv3/mission_info", 
        "usv3/mission_info/mission_log", "usv3/mission_info/route", 
        "usv3/mission_info/antennas", "usv3/mission_info/antennas/antenna1", 
        "usv3/mission_info/antennas/antenna2", "usv3/mission_info/antennas/antenna3", 
        "usv3/mission_info/sensors", "usv3/mission_info/sensors/sensor1", 
        "usv3/mission_info/sensors/sensor2", "usv3/mission_info/sensors/sensor3", 
        "usv3/mission_info/location", "usv3/health_info/log", 
        "usv3/health_info/antenna_conditions/antenna1", 
        "usv3/health_info/antenna_conditions/antenna2", 
        "usv3/health_info/antenna_conditions/antenna3", 
        "usv3/health_info/sensor_conditions/sensor1", 
        "usv3/health_info/sensor_conditions/sensor2", 
        "usv3/health_info/sensor_conditions/sensor3", "usv3/health_info/battery_level"]
usv4 = ["usv4", "usv4/health_info", "usv4/mission_info", 
        "usv4/mission_info/mission_log", "usv4/mission_info/route", 
        "usv4/mission_info/antennas", "usv4/mission_info/antennas/antenna1", 
        "usv4/mission_info/antennas/antenna2", "usv4/mission_info/antennas/antenna3", 
        "usv4/mission_info/sensors", "usv4/mission_info/sensors/sensor1", 
        "usv4/mission_info/sensors/sensor2", "usv4/mission_info/sensors/sensor3", 
        "usv4/mission_info/location", "usv4/health_info/log", 
        "usv4/health_info/antenna_conditions/antenna1", 
        "usv4/health_info/antenna_conditions/antenna2", 
        "usv4/health_info/antenna_conditions/antenna3", 
        "usv4/health_info/sensor_conditions/sensor1", 
        "usv4/health_info/sensor_conditions/sensor2", 
        "usv4/health_info/sensor_conditions/sensor3", "usv4/health_info/battery_level"]
# 2D list with a list of name lists ordered by node id
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
# hit_distances list keeps track of how many nodes each interest must 
# pass through before a node has the data being requested
# hit_distances indexes match interest ids, each time an interest is 
# created 0 is appended to hit_distances
# each time a node receives a request it adds one to the hit_distances 
# list where the index equals the interest id
hit_distances = []
return_times = []
# cache status keeps track of the number of current caches of each data 
# name across the network
cache_status = {}
for r in range(0, len(node_names)):
    for n in node_names[r]:
        cache_status[n] = 0
# hits and times list are used for the graph of cache hits
# every time a node is able to satisfy a request with data from its 
# content store it appends 1 to the hits list and the current 
# environment time to the times list
hits = []
times = []
# creating an list of content for the forwarding interest base of each 
# node, ordered by node id
# each node has a dictionary for the content of its forwarding interest 
# base, the keys are data names and the values are the channel indexes to forward requests to
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
# getting results from ndnProjectNetwork file, which are in the form of 
# a dictionary
results = network.graph_configuration()
H = results["graph"]
# ndnProjectNetwork sends a 2D list of edge channels with each item 
# having the structure of [channel id, node channel is connected to, 
# channel length]
# these are not part of the networkx graph since they are only connected 
# to one node on the edge of the graph
edge_channels = results["edge_channels"]
# past variable keeps track of channel ids as they're being added so 
# that edge channel ids can be added at the right index in the 
# channel list
past = -1
for e in H.edges:
    # checking if any edge channels should be added to channels list
    for r in edge_channels:
        # if edge channel id is between the past id and the current id, the channel will be added to the channels list using the attributes defined in the edge_channels lists
        if r["id"] > past and r["id"] < H.edges[e]["id"]:
            channels.append(Channel(env, r["id"], [-1, r["node"]], r["length"]))
    #channel objects are created and added using the graph edges and their attributes
    channels.append(Channel(env, H.edges[e]["id"], [e[0], e[1]], H.edges[e]["length"]))
    past = H.edges[e]["id"]
for n in H.nodes:
    #keeps track of channel ids connected to the node, reset each time
    c_ids = []
    #checking graph edges for connected channels
    for e in H.edges(n):
        c_ids.append(H.edges[e]["id"])
    #checking edge channels
    for r in edge_channels:
        if r["node"] == n:
            c_ids.append(r["id"])
    logging.info(node_names[n][0])
    #creating the node object and adding
    nodes.append(Node(env, n, node_names[n][0], c_ids, CACHE_SIZE, 5, content[n], []))
#creating the queue of environment processes
#interest_arrival generates interests
env.process(interest_arrival())
#for each channel conncted to a node object a function is called to search for new entries in the channel's data and interest stores
#channel order in each node is changed each time around
for n in nodes:
    for i in range(0, len(n.channel_ids)):
        env.process(n.search_interests(n.channel_ids[i]))
        env.process(n.search_data(n.channel_ids[i]))
#these lists keep track of where the data for each run starts
hd_indexes = []
rt_indexes = []
for i in range(0, SAMPLES):
    hd_indexes.append(len(hit_distances) - 1)
    rt_indexes.append(len(rt_indexes) - 1)
    env.run(until=env.now + RUN_TIME)
    for n in nodes:
        n.content_store.content = []
    for c in cache_status:
        cache_status[c] = 0
#calculating the average cache hit ratio
#total calculates the total number of cache hits
#length counts the total number of requests the nodes have received
total = 0
length = 0
for n in nodes:
    if type(n) == Node and n.total_requests != 0:
        total += n.cache_hits/n.total_requests
        length += 1
logging.info("Average cache hit ratio: %s", total/length)
#log the average hit distance
logging.info("Average hit distance: %s", statistics.mean(hit_distances))
#log the average return time
logging.info("Average return time: %s", statistics.mean(return_times))
logging.info(hd_indexes)
hd_averages = []
for i in range(0, len(hd_indexes) - 1):
    hd_averages.append(statistics.mean(hit_distances[hd_indexes[i]+1:hd_indexes[i+1]+1]))
hd_averages.append(statistics.mean(hit_distances[hd_indexes[len(hd_indexes)-1]+1:]))
rt_averages = []
for i in range(0, len(rt_indexes) - 1):
    rt_averages.append(statistics.mean(return_times[rt_indexes[i]+1:rt_indexes[i+1]+1]))
rt_averages.append(statistics.mean(return_times[rt_indexes[len(rt_indexes)-1]+1:]))
seaborn.histplot(hd_averages)
plt.xlabel("Average Hit Distance in a Run")
plt.ylabel("Frequency")
mean = statistics.mean(hit_distances)
plt.title("Hit Distances Histogram With " + str(PROB) + " Probability of Caching: Mean = " + str(mean))
plt.show()
seaborn.histplot(rt_averages)
plt.xlabel("Average Return Time in a Run")
plt.ylabel("Frequency")
mean = statistics.mean(return_times)
plt.title("Return Times Histogram With " + str(PROB) + " Probability of Caching: Mean = " + str(mean))
plt.show()
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