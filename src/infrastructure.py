from faas import Node


class Region:

    def __init__(self, name: str, is_cloud=True):
        self.name = name
        self.cloud = is_cloud

    def is_cloud(self):
        return self.cloud

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return self.name


class Network:

    def __init__(self, regions: [Region], network_latency: dict, bandwidth_mbps: dict):
        self.regions = regions
        self.latency = network_latency
        self.bandwidth_mbps = bandwidth_mbps
        self.region_nodes = {r: [] for r in self.regions}
        self.region_dict = {r.name: r for r in self.regions}
        self.node2neighbors = {}

    def get_latency(self, x: Node, y: Node):
        if x == y:
            # same node
            return 0.0

        if (x, y) in self.latency:
            return self.latency[(x, y)]
        elif (y, x) in self.latency:
            self.latency[(x, y)] = self.latency[(y, x)]
            return self.latency[(x, y)]
        else:
            return self.get_region_latency(x.region, y.region)

    def get_region_latency(self, x: Region, y: Region):
        if x == y and not (x, y) in self.latency:
            # same region default
            return 0.005

        if (x, y) in self.latency:
            return self.latency[(x, y)]
        elif (y, x) in self.latency:
            self.latency[(x, y)] = self.latency[(y, x)]
            return self.latency[(x, y)]

        raise KeyError(f"no latency specified for {x} and {y}")

    def get_bandwidth(self, x: Node, y: Node):
        if x == y:
            # same node
            return float("inf")

        if (x, y) in self.bandwidth_mbps:
            return self.bandwidth_mbps[(x, y)]
        elif (y, x) in self.bandwidth_mbps:
            self.bandwidth_mbps[(x, y)] = self.bandwidth_mbps[(y, x)]
            return self.bandwidth_mbps[(x, y)]
        else:
            return self.get_region_bandwidth(x.region, y.region)

    def get_region_bandwidth(self, x: Region, y: Region):
        if (x, y) in self.bandwidth_mbps:
            return self.bandwidth_mbps[(x, y)]
        elif (y, x) in self.bandwidth_mbps:
            self.bandwidth_mbps[(x, y)] = self.bandwidth_mbps[(y, x)]
            return self.bandwidth_mbps[(x, y)]

        raise KeyError(f"no bandwidth_mbps specified for {x} and {y}")

    def get_region(self, reg_name: str) -> Region:
        return self.region_dict[reg_name]

    def add_node(self, node, region: Region):
        self.region_nodes[region].append(node)

    def get_edge_nodes(self):
        nodes = []
        for r in self.regions:
            if not r.is_cloud():
                nodes.extend(self.region_nodes[r])
        return nodes

    def get_cloud_nodes(self):
        nodes = []
        for r in self.regions:
            if r.is_cloud():
                nodes.extend(self.region_nodes[r])
        return nodes

    def get_nodes(self):
        nodes = []
        for r in self.regions:
            nodes.extend(self.region_nodes[r])
        return nodes

    def get_region_nodes(self, reg):
        return self.region_nodes[reg]

    def get_neighbors(self, node, node_choice_rng, max_peers=3):
        if node in self.node2neighbors:
            peers = self.node2neighbors[node]
        else:
            peers = self.get_region_nodes(node.region).copy()
            peers.remove(node)
            self.node2neighbors[node] = peers

        if 0 < max_peers < len(peers):
            return node_choice_rng.choice(peers, max_peers)  # TODO: random selection
        else:
            return peers

    def __repr__(self):
        s = ""
        for r in self.regions:
            s += f"-------- {r} (is_cloud: {r.is_cloud()}) -------\n"
            for n in self.region_nodes[r]:
                s += repr(n) + "\n"
        return s


if __name__ == "__main__":
    # TODO set regions, latency and bandwidth from config
    region_cloud = Region("cloud", True)
    region_edge1 = Region("edge1", False)
    region_edge2 = Region("edge2", False)
    regions = [region_cloud, region_edge1, region_edge2]
    net_latency = {}
    bandwidth_mbps = {}

    # Add node cloud
    network = Network(regions=regions, network_latency=net_latency, bandwidth_mbps=bandwidth_mbps)
    network.add_node(Node("nuvola", 1000, region=region_cloud, speedup=1), region=region_cloud)
    network.add_node(Node("pippo", 100, region=region_edge1, speedup=1), region=region_edge1)
    network.add_node(Node("pluto", 100, region=region_edge1, speedup=1), region=region_edge1)
    network.add_node(Node("topolino", 100, region=region_edge2, speedup=1), region=region_edge2)
    print(network)