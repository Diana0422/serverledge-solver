import unittest
import registry as r


class TestRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(self) -> None:
        self.registry_cli = r.Registry()

    def test_client(self):
        self.assertNotEquals(self.registry_cli, None, "registry not initialized")
        self.assertEquals(self.registry_cli.client.base_uri, "http://127.0.0.1:2379", "URI not correct")

    def test_read(self):
        print(self.registry_cli.client.get("/registry/ROME/P3nfFLsDf7edYaiuhhfQtR1694879263727288922/"))

    def test_write(self):
        self.registry_cli.write_registry()
