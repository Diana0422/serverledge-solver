import unittest
import src.server as s


class TestNetworkInit(unittest.TestCase):
    def test_init_network(self):
        network = s.initializing_network()
        self.assertNotEquals(network, None, "Network not initialized")


class TestNetworkMetrics(unittest.TestCase):

    @classmethod
    def setUpClass(self) -> None:
        self.metrics = s.NetworkMetrics(network=s.initializing_network())

    def test_update_aggregated_edge_memory(self):
        pass

    def test_update_bandwidth(self):
        pass

    def test_update_rtt(self):
        pass

    def test_update_arrival_rates(self):
        pass

    def test_update_service_time(self):
        pass

    def test_update_init_time(self):
        pass

    def test_update_cold_start(self):
        pass


class TestMembership(unittest.TestCase):

    @classmethod
    def setUpClass(self) -> None:
        self.metrics = s.NetworkMetrics(s.initializing_network())

    def test_node_arrival(self):
        local = s.update_membership()

    def test_node_exit(self):
        pass
