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
import csv
import datetime

logging.basicConfig(level = logging.INFO)

# User-set variables for simulation.

# Probability that data will be cached when caching through the CS.
PROB = 1

# Max size of a CS. 
CACHE_SIZE = 5

# Constants used to calculate delay in channrels.
BANDWIDTH = 100000000
SIGNAL_SPEED = 1500
# Range for random negative or positive variance in delay.
DELAY_VARIANCE = 0.5

# Data expires at different times depending on the importance.
# Health information expire time in seconds.
HI_EXPIRE_TIME = 500
# Mission information expire time in seconds.
MI_EXPIRE_TIME = 30

SAMPLES = 10000
RUN_TIME = 1000


class ContentStore(object):
    """Represents the Content Store (CS) of a node and its functions.

    Arguments:
    env -- Simpy env in which the simulation takes place
    max -- int representing the max amount of data the CS can hold
    content -- list of data packages the CS holds
    node_id -- int, id of the node the CS belongs to"""

    def __init__(self, env, max, content, node_id):
        self.env = env
        # max_size is currently is defined by CACHE_SIZE.
        self.max_size = max
        self.content = content
        self.node_id = node_id

    def search(self, interest):
        """Checks if the CS already contains the requested data. 
    
        Arguments:
        interest -- Interest object representing the request
        
        Returns: boolean"""

        # CS searches for data name, which also must not be expired.
        for d in self.content:
            if interest.data_name == d.name and d.expire_time > self.env.now:
                logging.debug("Data: %s found in Content Store", interest.data_name)
                # If found, return True.
                return True
            
        logging.debug("Data: %s not found in Content Store", interest.data_name)
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
                logging.debug("%s has expired and has been removed", d.name)

        numb = random.random()

        # CS will cache new data with pre-defined probability PROB.
        if numb < PROB:
            cache_status[data.name] += 1
            self.content.insert(0, data)
            
            # If size is too large, data will chosen to be removed.
            if len(self.content) > self.max_size:
                # The least desirable data will be set to the first entry.
                # The data's popularity will be used in its "score"
                if self.content[0].name in nodes[self.node_id].data_popularity:

                    min_score = nodes[self.node_id].data_popularity[
                        self.content[0].name]*(self.content[0].expire_time
                                               -self.env.now)
                # If popularity is not tracked by node, the score is 0.
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

            logging.debug("Cached %s in Content Store", data.name)

        else:
            logging.debug("Did not cache %s in Content Store", data.name)

        logging.debug("Current state of Content Store: %s", self.content)

    def send_data(self, channel_id, interest):
        """Creates Data object and sends it to the specified channel.
        
        Arguments:
        channel_id -- int, id of the channel which the request came from
        interest -- Interest object representing the request"""

        # Create new data object when responding with data.
        data = Data(self.env, interest.data_name)
        logging.debug("Responding with data: %s to channel %s", 
                     interest.data_name, channel_id)
        yield self.env.process(channels[channel_id].forward_data(data, interest, self.node_id))


class PendingInterest(object):
    """Represents the Pending Interest Table (PIT) of a node 
    and its functions.

    Arguments:
    env -- Simpy env in which the simulation takes place
    max -- int which specifies the max size of the PIT"""

    def __init__(self, env, max):
        self.env = env
        # max_size isn't currently being used for size management
        self.max_size = max
        # Dictionary with data names as keys and dictionaries as values.
        # The values are interest objects corresponding with channel ids.
        self.content = {}

    def search(self, interest):
        """Checks if the data name requested by the interest is already 
        in the PIT.
        
        Arguments:
        interest -- Interest object representing the request
        
        Returns: boolean"""

        # Check if the node has already forwarded a request for the data.
        if interest.data_name in self.content:
            logging.debug("Data: %s found in Pending Interest Table", interest.data_name)
            # Return True if found.
            return True
        
        logging.debug("Data: %s not found in Pending Interest Table", interest.data_name)
        # Otherwise, return False.
        return False
    
    def add_name(self, interest, fromId):
        """Adds new request to the content of the PIT.
        
        Arguments:
        interest -- Interest object representing the request
        fromId -- int, id for the channel the interest came through"""

        self.content[interest.data_name] = {interest: fromId}
        logging.debug("Data: %s added to Pending Interest Table", interest.data_name)

    def add_interface(self, interest, fromId):
        """Adds Interest object and channel id to an already-existing 
        entry for the data name.

        Arguments:
        interest -- Interest object representing the request
        fromId -- int, the channel id the interest came from"""

        self.content[interest.data_name][interest] = fromId
        logging.debug("Interface: %s added to %s in Pending Interest Table", 
                     fromId, interest.data_name)
        
    def remove(self, data_name):
        """Removes entry in PIT; called when the node receives the data.
        
        Arguments:
        data_name -- String which corresponds to the name of the data"""

        self.content.pop(data_name)
        logging.debug("Data: %s removed from Pending Interest Table", data_name)


class ForwardingBase(object):
    """Represents the Forwarding Information Base (FIB) of a node and 
    its functions.
    
    Arguments:
    env -- Simpy env in which the simulation takes place
    interfaces -- dictionary matching data names to channel ids
    node_id -- int, id of the node the FIB belongs to"""

    def __init__(self, env, interfaces, node_id):
        self.env = env
        # Dictionary with data names corresponding to channel ids.
        self.content = interfaces
        self.node_id = node_id

    def send_request(self, interest):
        """Sends Interest object to a channel based on the FIB's content.
        
        Arguments:
        interest -- Interest object representing the request"""

        logging.debug("Sending request for %s to Channel: %s", interest.data_name, 
                     self.content[interest.data_name])
        # FIB uses content to find the channel to forward the request to.
        yield self.env.process(
            channels[self.content[interest.data_name]].forward_interest(
                interest, self.node_id))
        

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

        # The channel determines which node to forward the interest to.
        if self.nodes[0] == node_id:
            rnode_id = self.nodes[1]

        else:
            rnode_id = self.nodes[0]

        logging.debug("Channel %s forwarding request for %s to %s", self.id, 
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

        # The channel determines which node to forward the data to.
        if self.nodes[0] == node_id:
            rnode_id = self.nodes[1]

        else:
            rnode_id = self.nodes[0]

        # Nodes with ids of -1 represent requesting users.
        # If the receiving node id = 1, the request is being satisfied.
        if rnode_id == -1:
            logging.debug("Returning data: %s to user", data.name)
            # Calculate and log how long it took to satisfy the interest.
            return_time = self.env.now - interest.creation_time
            return_times.append(return_time)

        else:
            logging.debug("Channel %s forwarding %s to %s", self.id, data.name, rnode_id)
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
        # Currently all interest packets are the same size.
        self.size = 1000


class Data(object):
    """Represents a data package and its attributes.
    
    Arguments:
    env -- Simpy env in which the simulation takes place
    id -- int, the id the data is assigned to
    name -- String, name of data being packaged"""

    def __init__(self, env, name):
        self.env = env
        self.name = name
        # Size of data is variable.
        self.size = 2000 + random.uniform(-200, 200)

        self.send_time = self.env.now
        # The time the data expires is determined based on importance.
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

        # Dictionary of stores (simpy resources) for interests received.
        self.stores = {}
        # Dictionary of stores (simpy resources) for data received.
        self.data_stores = {}

        self.channel_ids = channel_ids
        # Each channel is a value which corresponds to its own store.
        for x in channel_ids:
            self.stores[x] = simpy.Store(env)
            self.data_stores[x] = simpy.Store(env)

        # Creating instances of the three main parts of each node.
        self.content_store = ContentStore(self.env, cssize, cscontent, self.id)
        self.pending_interest = PendingInterest(self.env, pisize)
        self.forwarding_base = ForwardingBase(self.env, fbdata, self.id)

        # Dictionary which has data corresponding with times requested.
        self.data_popularity = {}

        # Keeps track of how many times a node finds requested data in its CS.
        self.cache_hits = 0
        # Keeps track of how many total interests pass through the node.
        self.total_requests = 0

    def search_interests(self, storeNum):
        """Gets an interest from specified request store, will break if 
        store is empty.
        
        Arguments:
        storeNum: int, the id of the channel associated with the store"""

        while True:
            # Function will stop if yield returns nothing.
            intrst = yield self.stores[storeNum].get()
            # If the function continues, the node receives the request.
            yield self.env.process(self.receive_request(intrst, storeNum))

    def search_data(self, storeNum):
        """Gets a data package from specified data store, will break if 
        store is empty.
        
        Arguments:
        storeNum: int, the id of the channel associated with the store"""

        while True:
            # If checking the last channel, the list will be shuffled.
            # This ensures the node is not biased towards one channel.
            if storeNum == self.channel_ids[len(self.channel_ids) - 1]:
                random.shuffle(self.channel_ids)

            # Function will stop if yield returns nothing
            data = yield self.data_stores[storeNum].get()
            # If the function continues, the node receives the data.
            yield self.env.process(self.receive_data(data))

    def receive_request(self, interest, fromchannel_id):
        """Processes an interest found while searching stores.
        
        Arguments:
        interest -- Interest object representing request
        fromchannel_id -- id of channel interest came from"""

        logging.debug("Node %s receiving request for %s", self.id, interest.data_name)
        # total_hits goes up by one when receiving an interest.
        self.total_requests += 1
        # The interest's hit distance also goes up by one.
        hit_distances[interest.id] += 1

        if interest.data_name in self.data_popularity:
            self.data_popularity[interest.data_name] += 1

        else:
            self.data_popularity[interest.data_name] = 1

        # Check if the node is the producer for the data requested. 
        if interest.data_name.startswith(self.name):
            # If it is the producer, create data packet and send it back.
            logging.debug("%s receiving request for %s", self.name, interest.data_name)
            data = Data(self.env, interest.data_name)
            logging.debug("Responding with data: %s to channel %s", 
                         interest.data_name, fromchannel_id)
            yield self.env.process(channels[fromchannel_id].forward_data(data, interest, 
                                                                       self.id))
            
        # below checks if the requested data is in the node's CS, if so, it 
        # creates a data packet and sends it back
        elif self.content_store.search(interest):
            logging.debug("Going to respond with data...")
            # cache hits goes up by one
            self.cache_hits += 1
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

        logging.debug("Node %s receiving data: %s", self.id, data.name)

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

    # Interest ids start at 0
    interest_id = 0

    # Create the list of edge channels to send interests through.
    channel_ids = []
    for e in edge_channels:
        channel_ids.append(e["id"])
    
    while True:
        yield env.timeout(random.uniform(0.5, 1.5))  

        if random.random() < 0.3:
            nodenum = 13

        else:
            # Generate a random data producer to request data from.
            nodenum = random.randint(0, len(node_names)-1) 

        # Below the data name is specified while creating the interest.
        interest = Interest(env, interest_id, 
                            node_names[nodenum][
                                random.randint(0, len(node_names[nodenum])-1)])
        
        # Create a new entry in hit distances list.
        hit_distances.append(0)

        logging.debug("About to send request for %s", interest.data_name)
        # New interests will be sent through random edge channel.
        yield env.process(channels[random.choice(channel_ids)].forward_interest(interest, -1))
        interest_id += 1

env = simpy.Environment()

# Lists for nodes and channels keep track of Node and Channel objects.
nodes = []
channels = []

# Defining data names for each data-producing node.
uuv_names = ["uuv", "uuv/health_info", "uuv/mission_info", "uuv/mission_info/mission_log", "uuv/mission_info/route", "uuv/mission_info/antennas", "uuv/mission_info/antennas/antenna1", "uuv/mission_info/antennas/antenna2", "uuv/mission_info/antennas/antenna3", "uuv/mission_info/sensors", "uuv/mission_info/sensors/sensor1", "uuv/mission_info/sensors/sensor2", "uuv/mission_info/sensors/sensor3", "uuv/mission_info/location", "uuv/mission_info/depth", "uuv/health_info/log", "uuv/health_info/antenna_conditions/antenna1", "uuv/health_info/antenna_conditions/antenna2", "uuv/health_info/antenna_conditions/antenna3", "uuv/health_info/sensor_conditions/sensor1", "uuv/health_info/sensor_conditions/sensor2", "uuv/health_info/sensor_conditions/sensor3", "uuv/health_info/battery_level"]
uuv1 = ["uuv1", "uuv1/health_info", "uuv1/mission_info", "uuv1/mission_info/mission_log", "uuv1/mission_info/route", "uuv1/mission_info/antennas", "uuv1/mission_info/antennas/antenna1", "uuv1/mission_info/antennas/antenna2", "uuv1/mission_info/antennas/antenna3", "uuv1/mission_info/sensors", "uuv1/mission_info/sensors/sensor1", "uuv1/mission_info/sensors/sensor2", "uuv1/mission_info/sensors/sensor3", "uuv1/mission_info/location", "uuv1/mission_info/depth", "uuv1/health_info/log", "uuv1/health_info/antenna_conditions/antenna1", "uuv1/health_info/antenna_conditions/antenna2", "uuv1/health_info/antenna_conditions/antenna3", "uuv1/health_info/sensor_conditions/sensor1", "uuv1/health_info/sensor_conditions/sensor2", "uuv1/health_info/sensor_conditions/sensor3", "uuv1/health_info/battery_level"]
uuv2 = ["uuv2", "uuv2/health_info", "uuv2/mission_info", "uuv2/mission_info/mission_log", "uuv2/mission_info/route", "uuv2/mission_info/antennas", "uuv2/mission_info/antennas/antenna1", "uuv2/mission_info/antennas/antenna2", "uuv2/mission_info/antennas/antenna3", "uuv2/mission_info/sensors", "uuv2/mission_info/sensors/sensor1", "uuv2/mission_info/sensors/sensor2", "uuv2/mission_info/sensors/sensor3", "uuv2/mission_info/location", "uuv2/mission_info/depth", "uuv2/health_info/log", "uuv2/health_info/antenna_conditions/antenna1", "uuv2/health_info/antenna_conditions/antenna2", "uuv2/health_info/antenna_conditions/antenna3", "uuv2/health_info/sensor_conditions/sensor1", "uuv2/health_info/sensor_conditions/sensor2", "uuv2/health_info/sensor_conditions/sensor3", "uuv2/health_info/battery_level"]
uuv3 = ["uuv3", "uuv3/health_info", "uuv3/mission_info", "uuv3/mission_info/mission_log", "uuv3/mission_info/route", "uuv3/mission_info/antennas", "uuv3/mission_info/antennas/antenna1", "uuv3/mission_info/antennas/antenna2", "uuv3/mission_info/antennas/antenna3", "uuv3/mission_info/sensors", "uuv3/mission_info/sensors/sensor1", "uuv3/mission_info/sensors/sensor2", "uuv3/mission_info/sensors/sensor3", "uuv3/mission_info/location", "uuv3/mission_info/depth", "uuv3/health_info/log", "uuv3/health_info/antenna_conditions/antenna1", "uuv3/health_info/antenna_conditions/antenna2", "uuv3/health_info/antenna_conditions/antenna3", "uuv3/health_info/sensor_conditions/sensor1", "uuv3/health_info/sensor_conditions/sensor2", "uuv3/health_info/sensor_conditions/sensor3", "uuv3/health_info/battery_level"]
uuv4 = ["uuv4", "uuv4/health_info", "uuv4/mission_info", "uuv4/mission_info/mission_log", "uuv4/mission_info/route", "uuv4/mission_info/antennas", "uuv4/mission_info/antennas/antenna1", "uuv4/mission_info/antennas/antenna2", "uuv4/mission_info/antennas/antenna3", "uuv4/mission_info/sensors", "uuv4/mission_info/sensors/sensor1", "uuv4/mission_info/sensors/sensor2", "uuv4/mission_info/sensors/sensor3", "uuv4/mission_info/location", "uuv4/mission_info/depth", "uuv4/health_info/log", "uuv4/health_info/antenna_conditions/antenna1", "uuv4/health_info/antenna_conditions/antenna2", "uuv4/health_info/antenna_conditions/antenna3", "uuv4/health_info/sensor_conditions/sensor1", "uuv4/health_info/sensor_conditions/sensor2", "uuv4/health_info/sensor_conditions/sensor3", "uuv4/health_info/battery_level"]
uuv5 = ["uuv5", "uuv5/health_info", "uuv5/mission_info", "uuv5/mission_info/mission_log", "uuv5/mission_info/route", "uuv5/mission_info/antennas", "uuv5/mission_info/antennas/antenna1", "uuv5/mission_info/antennas/antenna2", "uuv5/mission_info/antennas/antenna3", "uuv5/mission_info/sensors", "uuv5/mission_info/sensors/sensor1", "uuv5/mission_info/sensors/sensor2", "uuv5/mission_info/sensors/sensor3", "uuv5/mission_info/location", "uuv5/mission_info/depth", "uuv5/health_info/log", "uuv5/health_info/antenna_conditions/antenna1", "uuv5/health_info/antenna_conditions/antenna2", "uuv5/health_info/antenna_conditions/antenna3", "uuv5/health_info/sensor_conditions/sensor1", "uuv5/health_info/sensor_conditions/sensor2", "uuv5/health_info/sensor_conditions/sensor3", "uuv5/health_info/battery_level"]
uuv6 = ["uuv6", "uuv6/health_info", "uuv6/mission_info", "uuv6/mission_info/mission_log", "uuv6/mission_info/route", "uuv6/mission_info/antennas", "uuv6/mission_info/antennas/antenna1", "uuv6/mission_info/antennas/antenna2", "uuv6/mission_info/antennas/antenna3", "uuv6/mission_info/sensors", "uuv6/mission_info/sensors/sensor1", "uuv6/mission_info/sensors/sensor2", "uuv6/mission_info/sensors/sensor3", "uuv6/mission_info/location", "uuv6/mission_info/depth", "uuv6/health_info/log", "uuv6/health_info/antenna_conditions/antenna1", "uuv6/health_info/antenna_conditions/antenna2", "uuv6/health_info/antenna_conditions/antenna3", "uuv6/health_info/sensor_conditions/sensor1", "uuv6/health_info/sensor_conditions/sensor2", "uuv6/health_info/sensor_conditions/sensor3", "uuv6/health_info/battery_level"]
uuv7 = ["uuv7", "uuv7/health_info", "uuv7/mission_info", "uuv7/mission_info/mission_log", "uuv7/mission_info/route", "uuv7/mission_info/antennas", "uuv7/mission_info/antennas/antenna1", "uuv7/mission_info/antennas/antenna2", "uuv7/mission_info/antennas/antenna3", "uuv7/mission_info/sensors", "uuv7/mission_info/sensors/sensor1", "uuv7/mission_info/sensors/sensor2", "uuv7/mission_info/sensors/sensor3", "uuv7/mission_info/location", "uuv7/mission_info/depth", "uuv7/health_info/log", "uuv7/health_info/antenna_conditions/antenna1", "uuv7/health_info/antenna_conditions/antenna2", "uuv7/health_info/antenna_conditions/antenna3", "uuv7/health_info/sensor_conditions/sensor1", "uuv7/health_info/sensor_conditions/sensor2", "uuv7/health_info/sensor_conditions/sensor3", "uuv7/health_info/battery_level"]
uuv8 = ["uuv8", "uuv8/health_info", "uuv8/mission_info", "uuv8/mission_info/mission_log", "uuv8/mission_info/route", "uuv8/mission_info/antennas", "uuv8/mission_info/antennas/antenna1", "uuv8/mission_info/antennas/antenna2", "uuv8/mission_info/antennas/antenna3", "uuv8/mission_info/sensors", "uuv8/mission_info/sensors/sensor1", "uuv8/mission_info/sensors/sensor2", "uuv8/mission_info/sensors/sensor3", "uuv8/mission_info/location", "uuv8/mission_info/depth", "uuv8/health_info/log", "uuv8/health_info/antenna_conditions/antenna1", "uuv8/health_info/antenna_conditions/antenna2", "uuv8/health_info/antenna_conditions/antenna3", "uuv8/health_info/sensor_conditions/sensor1", "uuv8/health_info/sensor_conditions/sensor2", "uuv8/health_info/sensor_conditions/sensor3", "uuv8/health_info/battery_level"]
usv_names = ["usv", "usv/health_info", "usv/mission_info", "usv/mission_info/mission_log", "usv/mission_info/route", "usv/mission_info/antennas", "usv/mission_info/antennas/antenna1", "usv/mission_info/antennas/antenna2", "usv/mission_info/antennas/antenna3", "usv/mission_info/sensors", "usv/mission_info/sensors/sensor1", "usv/mission_info/sensors/sensor2", "usv/mission_info/sensors/sensor3", "usv/mission_info/location", "usv/health_info/log", "usv/health_info/antenna_conditions/antenna1", "usv/health_info/antenna_conditions/antenna2", "usv/health_info/antenna_conditions/antenna3", "usv/health_info/sensor_conditions/sensor1", "usv/health_info/sensor_conditions/sensor2", "usv/health_info/sensor_conditions/sensor3", "usv/health_info/battery_level"]
usv1 = ["usv1", "usv1/health_info", "usv1/mission_info", "usv1/mission_info/mission_log", "usv1/mission_info/route", "usv1/mission_info/antennas", "usv1/mission_info/antennas/antenna1", "usv1/mission_info/antennas/antenna2", "usv1/mission_info/antennas/antenna3", "usv1/mission_info/sensors", "usv1/mission_info/sensors/sensor1", "usv1/mission_info/sensors/sensor2", "usv1/mission_info/sensors/sensor3", "usv1/mission_info/location", "usv1/health_info/log", "usv1/health_info/antenna_conditions/antenna1", "usv1/health_info/antenna_conditions/antenna2", "usv1/health_info/antenna_conditions/antenna3", "usv1/health_info/sensor_conditions/sensor1", "usv1/health_info/sensor_conditions/sensor2", "usv1/health_info/sensor_conditions/sensor3", "usv1/health_info/battery_level"]
usv2 = ["usv2", "usv2/health_info", "usv2/mission_info", "usv2/mission_info/mission_log", "usv2/mission_info/route", "usv2/mission_info/antennas", "usv2/mission_info/antennas/antenna1", "usv2/mission_info/antennas/antenna2", "usv2/mission_info/antennas/antenna3", "usv2/mission_info/sensors", "usv2/mission_info/sensors/sensor1", "usv2/mission_info/sensors/sensor2", "usv2/mission_info/sensors/sensor3", "usv2/mission_info/location", "usv2/health_info/log", "usv2/health_info/antenna_conditions/antenna1", "usv2/health_info/antenna_conditions/antenna2", "usv2/health_info/antenna_conditions/antenna3", "usv2/health_info/sensor_conditions/sensor1", "usv2/health_info/sensor_conditions/sensor2", "usv2/health_info/sensor_conditions/sensor3", "usv2/health_info/battery_level"]
usv3 = ["usv3", "usv3/health_info", "usv3/mission_info", "usv3/mission_info/mission_log", "usv3/mission_info/route", "usv3/mission_info/antennas", "usv3/mission_info/antennas/antenna1", "usv3/mission_info/antennas/antenna2", "usv3/mission_info/antennas/antenna3", "usv3/mission_info/sensors", "usv3/mission_info/sensors/sensor1", "usv3/mission_info/sensors/sensor2", "usv3/mission_info/sensors/sensor3", "usv3/mission_info/location", "usv3/health_info/log", "usv3/health_info/antenna_conditions/antenna1", "usv3/health_info/antenna_conditions/antenna2", "usv3/health_info/antenna_conditions/antenna3", "usv3/health_info/sensor_conditions/sensor1", "usv3/health_info/sensor_conditions/sensor2", "usv3/health_info/sensor_conditions/sensor3", "usv3/health_info/battery_level"]
usv4 = ["usv4", "usv4/health_info", "usv4/mission_info", "usv4/mission_info/mission_log", "usv4/mission_info/route", "usv4/mission_info/antennas", "usv4/mission_info/antennas/antenna1", "usv4/mission_info/antennas/antenna2", "usv4/mission_info/antennas/antenna3", "usv4/mission_info/sensors", "usv4/mission_info/sensors/sensor1", "usv4/mission_info/sensors/sensor2", "usv4/mission_info/sensors/sensor3", "usv4/mission_info/location", "usv4/health_info/log", "usv4/health_info/antenna_conditions/antenna1", "usv4/health_info/antenna_conditions/antenna2", "usv4/health_info/antenna_conditions/antenna3", "usv4/health_info/sensor_conditions/sensor1", "usv4/health_info/sensor_conditions/sensor2", "usv4/health_info/sensor_conditions/sensor3", "usv4/health_info/battery_level"]
usv5 = ["usv5", "usv5/health_info", "usv5/mission_info", "usv5/mission_info/mission_log", "usv5/mission_info/route", "usv5/mission_info/antennas", "usv5/mission_info/antennas/antenna1", "usv5/mission_info/antennas/antenna2", "usv5/mission_info/antennas/antenna3", "usv5/mission_info/sensors", "usv5/mission_info/sensors/sensor1", "usv5/mission_info/sensors/sensor2", "usv5/mission_info/sensors/sensor3", "usv5/mission_info/location", "usv5/health_info/log", "usv5/health_info/antenna_conditions/antenna1", "usv5/health_info/antenna_conditions/antenna2", "usv5/health_info/antenna_conditions/antenna3", "usv5/health_info/sensor_conditions/sensor1", "usv5/health_info/sensor_conditions/sensor2", "usv5/health_info/sensor_conditions/sensor3", "usv5/health_info/battery_level"]
usv6 = ["usv6", "usv6/health_info", "usv6/mission_info", "usv6/mission_info/mission_log", "usv6/mission_info/route", "usv6/mission_info/antennas", "usv6/mission_info/antennas/antenna1", "usv6/mission_info/antennas/antenna2", "usv6/mission_info/antennas/antenna3", "usv6/mission_info/sensors", "usv6/mission_info/sensors/sensor1", "usv6/mission_info/sensors/sensor2", "usv6/mission_info/sensors/sensor3", "usv6/mission_info/location", "usv6/health_info/log", "usv6/health_info/antenna_conditions/antenna1", "usv6/health_info/antenna_conditions/antenna2", "usv6/health_info/antenna_conditions/antenna3", "usv6/health_info/sensor_conditions/sensor1", "usv6/health_info/sensor_conditions/sensor2", "usv6/health_info/sensor_conditions/sensor3", "usv6/health_info/battery_level"]

# 2D list with a list of name lists ordered by node id.
node_names = []
node_names.append(usv1)
node_names.append(uuv1)
node_names.append(uuv2)
node_names.append(usv2)
node_names.append(uuv3)
node_names.append(uuv4)
node_names.append(usv3)
node_names.append(uuv5)
node_names.append(uuv6)
node_names.append(usv4)
node_names.append(uuv7)
node_names.append(uuv8)
node_names.append(usv5)
node_names.append(usv6)

# hit_distances and return_times are ordered by corresponding interest id.
hit_distances = []
return_times = []

# Keeps track of the number of current caches of each data name.
cache_status = {}
for r in range(0, len(node_names)):
    for n in node_names[r]:
        cache_status[n] = 0

# Creating an list of content for the forwarding interest base of each node.
# Content is a dictionary with data names as keys and channel ids as values.
content = []

content1 = {}
for r in range(0, len(node_names)):
    for n in node_names[r]:
        content1[n] = 1

content.append(content1)

content2 = {}
for r in range(0, len(node_names)):
    if r == 0:
        for n in node_names[r]:
            content2[n] = 1
    else:
        for n in node_names[r]:
            content2[n] = 1
content.append(content2)

content3 = {}
for r in range(0, len(node_names)):
    if r < 2:
        for n in node_names[r]:
            content3[n] = 2
    else:
        for n in node_names[r]:
            content3[n] = 3
content.append(content3)

content4 = {}
for r in range(0, len(node_names)):
    for n in node_names[r]:
        content4[n] = 5
content.append(content4)

content5 = {}
for r in range(0, len(node_names)):
    if r == 3:
        for n in node_names[r]:
            content5[n] = 5
    else:
        for n in node_names[r]:
            content5[n] = 6
content.append(content5)

content6 = {}
for r in range(0, len(node_names)):
    if r < 5 and r > 2:
        for n in node_names[r]:
            content6[n] = 6
    else:
        for n in node_names[r]:
            content6[n] = 7
content.append(content6)

content7 = {}
for r in range(0, len(node_names)):
    for n in node_names[r]:
        content7[n] = 9
content.append(content7)

content8 = {}
for r in range(0, len(node_names)):
    if r == 6:
        for n in node_names[r]:
            content8[n] = 9
    else:
        for n in node_names[r]:
            content8[n] = 10
content.append(content8)

content9 = {}
for r in range(0, len(node_names)):
    if r < 8 and r > 5:
        for n in node_names[r]:
            content9[n] = 10
    else:
        for n in node_names[r]:
            content9[n] = 11
content.append(content9)

content10 = {}
for r in range(0, len(node_names)):
    for n in node_names[r]:
        content10[n] = 13
content.append(content10)

content11 = {}
for r in range(0, len(node_names)):
    if r == 9:
        for n in node_names[r]:
            content11[n] = 13
    else:
        for n in node_names[r]:
            content11[n] = 14
content.append(content11)

content12 = {}
for r in range(0, len(node_names)):
    if r < 11 and r > 8:
        for n in node_names[r]:
            content12[n] = 14
    else:
        for n in node_names[r]:
            content12[n] = 15
content.append(content12)

content13 = {}
for r in range(0, len(node_names)):
    if r < 12 and r > 8:
        for n in node_names[r]:
            content13[n] = 15
    elif r < 9 and r > 5:
        for n in node_names[r]:
            content13[n] = 11
    else:
        for n in node_names[r]:
            content13[n] = 16
content.append(content13)

content14 = {}
for r in range(0, len(node_names)):
    if r < 6 and r > 2:
        for n in node_names[r]:
            content14[n] = 7
    elif r < 3:
        for n in node_names[r]:
            content14[n] = 3
    else:
        for n in node_names[r]:
            content14[n] = 16
content.append(content14)

# Getting results from network file, which are a dictionary.
results = network.graph_configuration()
H = results["graph"]
# network sends a list of edge channels, which are not part of the graph.
edge_channels = results["edge_channels"]

# Keeps track of ids so edge channels can be added at the right index.
past = -1

for e in H.edges:
    # Checking if any edge channels should be added to channels list.
    for r in edge_channels:
        # Add if edge channel id is between past and the current id.
        if r["id"] > past and r["id"] < H.edges[e]["id"]:
            # One of the ids for an edge channel's nodes is -1.
            channels.append(Channel(env, r["id"], [-1, r["node"]], 
                                    r["length"]))

    # Channel objects are created using attributes of graph edges.
    channels.append(Channel(env, H.edges[e]["id"], [e[0], e[1]], 
                            H.edges[e]["length"]))

    past = H.edges[e]["id"]

for n in H.nodes:
    # Keeps track of channel ids connected to the node, reset each time.
    c_ids = []

    # Check graph edges for connected channels.
    for e in H.edges(n):
        c_ids.append(H.edges[e]["id"])

    # Check if node is connected to an edge channel.
    for r in edge_channels:
        if r["node"] == n:
            c_ids.append(r["id"])
            
    # Pre-fill CS.
    cscontent = []
    for i in range(0, CACHE_SIZE):
        rand = random.randint(0, len(node_names) - 1)
        cscontent.append(Data(env, node_names[rand][
            random.randint(0, len(node_names[rand]) - 1)]))

    # Create the node object and add to nodes.
    nodes.append(Node(env, n, node_names[n][0], c_ids, CACHE_SIZE, 5, 
                      content[n], cscontent))

# Create the queue of environment processes.
env.process(interest_arrival())

# Search interest and data stores of each channel connected to a node.
for n in nodes:
    for i in range(0, len(n.channel_ids)):
        env.process(n.search_interests(n.channel_ids[i]))
        env.process(n.search_data(n.channel_ids[i]))

# These lists keep track of where the data for each run/sample starts.
hd_indexes = []
rt_indexes = []

for i in range(0, SAMPLES):
    hd_indexes.append(len(hit_distances) - 1)
    rt_indexes.append(len(rt_indexes) - 1)

    env.run(until = env.now + RUN_TIME)
    
    # Reset CS.
    for n in nodes:
        cscontent = []
        for i in range(0, CACHE_SIZE):
            rand = random.randint(0, len(node_names) - 1)
            cscontent.append(Data(env, node_names[rand][random.randint(
                0, len(node_names[rand]) - 1)]))

        n.content_store.content = cscontent
    
    # Reset cache_status.
    for c in cache_status:
        cache_status[c] = 0

# Calculate the average cache-hit ratio (cache_hits/total_requests).
total = 0
length = 0
for n in nodes:
    if type(n) == Node and n.total_requests != 0:
        total += n.cache_hits/n.total_requests
        length += 1

logging.info("Average cache hit ratio: %s", total/length)

# Log the average hit distance and variance.
logging.info("Average hit distance: %s", statistics.mean(hit_distances))
logging.info("Hit distance variance across all interests: %s", 
             statistics.variance(hit_distances))

# Log the average return time and variance.
logging.info("Average return time: %s", statistics.mean(return_times))
logging.info("Return time variance across all interests: %s", 
             statistics.variance(return_times))

logging.info("Percent 1: %s", 100 * hit_distances.count(1)/len(hit_distances))
logging.info("Percent 2: %s", 100 * hit_distances.count(2)/len(hit_distances))
logging.info("Percent 3: %s", 100 * hit_distances.count(3)/len(hit_distances))
logging.info("Percent 4: %s", 100 * hit_distances.count(4)/len(hit_distances))
logging.info("Percent 5: %s", 100 * hit_distances.count(5)/len(hit_distances))


# Find the average hit distance for each sample.
hd_averages = []
for i in range(0, len(hd_indexes) - 1):
    hd_averages.append(statistics.mean(hit_distances[
        hd_indexes[i] + 1:hd_indexes[i+1]+1]))

# Add last sample.
hd_averages.append(statistics.mean(hit_distances[
    hd_indexes[len(hd_indexes)-1]+1:]))

# Log variance.
logging.info("Hit distance variance across average hit distance of samples: %s", 
             statistics.variance(hd_averages))


# Find the average return time for each sample.
rt_averages = []
for i in range(0, len(rt_indexes) - 1):
    rt_averages.append(statistics.mean(return_times[
        rt_indexes[i]+1:rt_indexes[i+1]+1]))

# Add last sample.
rt_averages.append(statistics.mean(return_times[rt_indexes[
    len(rt_indexes)-1]+1:]))

#Log variance.
logging.info("Return time variance across average return time of samples: %s", 
             statistics.variance(rt_averages))


# Plot hit distance across samples.
seaborn.histplot(hd_averages)
plt.xlabel("Average Hit Distance in a Run")
plt.ylabel("Frequency")
mean = statistics.mean(hit_distances)
plt.title("Hit Distances Histogram With " + str(PROB) 
          + " Probability of Caching: Mean = " + str(round(mean, 4)))
plt.show()


# Plot return times across samples.
seaborn.histplot(rt_averages)
plt.xlabel("Average Return Time in a Run")
plt.ylabel("Frequency")
mean = statistics.mean(return_times)
plt.title("Return Times Histogram With " + str(PROB) 
          + " Probability of Caching: Mean = " + str(round(mean, 4)))
plt.show()


# Graph network.
center_node = nodes[13]
edge_nodes = set(H) - {center_node}
pos = nx.circular_layout(H.subgraph(edge_nodes))
pos[center_node] = numpy.array([0, 0])
nx.draw(H)
plt.draw()
plt.show()

with open("data.csv", "w", newline = '') as csvfile:
    field_names = ["Date", "Probability", "Sample Size", "Run Time", 
                   "Average Hit Distance", "HD Variance Across Interests", 
                   "HD Variance Across Samples", "HD Sample Averages", 
                   "Average Return Time", "RT Variance Across Interests",
                   "RT Variance Across Samples", "RT Sample Averages"]
    dwriter = csv.DictWriter(csvfile, fieldnames=field_names)
    dwriter.writeheader()
    dwriter.writerow({"Date": datetime.datetime.now, "Probability": PROB, 
                     "Sample Size": SAMPLES, "Run Time": RUN_TIME, 
                     "Average Hit Distance": statistics.mean(hit_distances), 
                     "HD Variance Across Interests": statistics.variance(hit_distances), 
                     "HD Variance Across Samples": statistics.variance(hd_averages), 
                     "HD Sample Averages": hd_averages,
                     "Average Return Time": statistics.mean(return_times),
                     "RT Variance Across Interests": statistics.variance(return_times),
                     "RT Variance Across Samples": statistics.variance(rt_averages),
                     "RT Sample Averages": rt_averages})