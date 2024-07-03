import networkx as nx
import matplotlib.pyplot as plt
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
    G.add_edge(0, 1, object = 1)
    G.add_edge(1, 2, object = 2)
    G.add_edge(2, 9, object = 3)
    G.add_edge(3, 4, object = 5)
    G.add_edge(4, 5, object = 6)
    G.add_edge(5, 9, object = 7)
    G.add_edge(6, 7, object = 9)
    G.add_edge(7, 8, object = 10)
    G.add_edge(8, 9, object = 11)
    edgeChannels.append([0, 0])
    edgeChannels.append([4, 3])
    edgeChannels.append([8, 6])
    data_producers = [9]
    results = {"graph": G, "edgeChannels": edgeChannels, "dataProducers": data_producers}
    return results
