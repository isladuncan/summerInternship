import networkx as nx
from numpy import random

def graph_configuration():
    """Sets up networkx graph and some node/channel attributes."""

    G = nx.Graph()
    nodes = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    edge_channels = []

    G.add_nodes_from(nodes)

    # Length (in meters) is randomly chosen for edges.
    G.add_edge(0, 1, id = 1, length = 1000)
    G.add_edge(1, 2, id = 2, length = 1000)
    G.add_edge(2, 13, id = 3, length = 1000)
    G.add_edge(3, 4, id = 5, length = 1000)
    G.add_edge(4, 5, id = 6, length = 1000)
    G.add_edge(5, 13, id = 7, length = 1000)
    G.add_edge(6, 7, id = 9, length = 1000)
    G.add_edge(7, 8, id = 10, length = 1000)
    G.add_edge(8, 12, id = 11, length = 1000)
    G.add_edge(9, 10, id = 13, length = 1000)
    G.add_edge(10, 11, id = 14, length = 1000)
    G.add_edge(11, 12, id = 15, length = 1000)
    G.add_edge(12, 13, id = 16, length = 1000)

    # Edge channels are not included in the graph, since they are only connected to one node on the edges of the graph.
    # Format for edge channel list: [id, node channel is connected to, length]
    edge_channels.append({"id": 0, "node": 0})
    edge_channels.append({"id": 4, "node": 3})
    edge_channels.append({"id": 8, "node": 6})
    edge_channels.append({"id": 12, "node": 9})
    for x in edge_channels:
        x["length"] = random.randint(500, 2000)

    # Send results back in a dictionary.
    results = {"graph": G, "edge_channels": edge_channels}
    return results