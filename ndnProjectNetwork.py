import networkx as nx
import matplotlib.pyplot as plt
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
    G.add_edge(0, 1, id = 1, length = random.randint(10, 1000))
    G.add_edge(1, 2, id = 2, length = random.randint(10, 1000))
    G.add_edge(2, 9, id = 3, length = random.randint(10, 1000))
    G.add_edge(3, 4, id = 5, length = random.randint(10, 1000))
    G.add_edge(4, 5, id = 6, length = random.randint(10, 1000))
    G.add_edge(5, 9, id = 7, length = random.randint(10, 1000))
    G.add_edge(6, 7, id = 9, length = random.randint(10, 1000))
    G.add_edge(7, 8, id = 10, length = random.randint(10, 1000))
    G.add_edge(8, 9, id = 11, length = random.randint(10, 1000))
    edgeChannels.append([0, 0])
    edgeChannels.append([4, 3])
    edgeChannels.append([8, 6])
    for x in edgeChannels:
        x.append(random.randint(500, 2000))
    data_producers = [9]
    results = {"graph": G, "edgeChannels": edgeChannels, "dataProducers": data_producers}
    return results
