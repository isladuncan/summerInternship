import networkx as nx
from numpy import random
def graphConfiguration():
    G = nx.Graph()
    nodes = []
    channels = []
    edgeChannels = []
    for i in range(0, 3):
        nodes.append(i)
        channels.append(i)
    channels.append(3)
    channels.append(4)
    channels.append(5)
    channels.append(6)
    channels.append(7)
    for i in range(3, 6):
        nodes.append(i)
    channels.append(8)
    for i in range(6, 9):
        nodes.append(i)
        channels.append(i+3)
    nodes.append(9)
    G.add_nodes_from(nodes)
    #length is randomly chosen for edges
    G.add_edge(0, 1, id = 1, length = random.randint(10, 1000))
    G.add_edge(1, 2, id = 2, length = random.randint(10, 1000))
    G.add_edge(2, 9, id = 3, length = random.randint(10, 1000))
    G.add_edge(3, 4, id = 4, length = random.randint(10, 1000))
    G.add_edge(4, 5, id = 5, length = random.randint(10, 1000))
    G.add_edge(5, 9, id = 6, length = random.randint(10, 1000))
    G.add_edge(6, 7, id = 8, length = random.randint(10, 1000))
    G.add_edge(7, 8, id = 9, length = random.randint(10, 1000))
    G.add_edge(8, 9, id = 10, length = random.randint(10, 1000))
    #edge channels are not included in the graph, since they are only connected to one node on the edges of the graph
    #format for edge channel list: [id, node channel is connected to, length]
    edgeChannels.append([0, 0])
    edgeChannels.append([7, 6])
    for x in edgeChannels:
        x.append(random.randint(500, 2000))
    #send results back in a dictionary
    results = {"graph": G, "edgeChannels": edgeChannels}
    return results