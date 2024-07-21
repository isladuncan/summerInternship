import networkx as nx
from numpy import random

def graph_configuration():
    """Sets up networkx graph and some node/channel attributes."""

    G = nx.Graph()
    nodes = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    edge_channels = []

    G.add_nodes_from(nodes)

    # Length (in meters) is randomly chosen for edges.
    G.add_edge(0, 1, id = 1, length = random.randint(10, 1000))
    G.add_edge(1, 2, id = 2, length = random.randint(10, 1000))
    G.add_edge(2, 9, id = 3, length = random.randint(10, 1000))
    G.add_edge(3, 4, id = 4, length = random.randint(10, 1000))
    G.add_edge(4, 5, id = 5, length = random.randint(10, 1000))
    G.add_edge(5, 9, id = 6, length = random.randint(10, 1000))
    G.add_edge(6, 7, id = 8, length = random.randint(10, 1000))
    G.add_edge(7, 8, id = 9, length = random.randint(10, 1000))
    G.add_edge(8, 9, id = 10, length = random.randint(10, 1000))

    # Edge channels are not included in the graph, since they are only connected to one node on the edges of the graph.
    # Format for edge channel list: [id, node channel is connected to, length]
    edge_channels.append({"id": 0, "node": 0})
    edge_channels.append({"id": 7, "node": 6})
    for x in edge_channels:
        x["length"] = random.randint(500, 2000)

    # Send results back in a dictionary.s
    results = {"graph": G, "edge_channels": edge_channels}
    return results