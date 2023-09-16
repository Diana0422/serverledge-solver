import etcd


class Registry:

    def __init__(self):
        self.client = etcd.Client(host='localhost', port=2379)  # etcd address: localhost:2379

    def read_registry(self):
        """
        Read node membership information from etcd
        :return: None
        """
        try:
            result = self.client.read('')
            print(result.value)
        except etcd.EtcdKeyNotFound:
            # do something
            print("error")

    def write_registry(self):
        x = self.client.write("/dir/name", "value", append=True)
        print("generated key: " + x.key)
        print("stored value: " + x.value)


if __name__ == "__main__":
    registry = Registry()
    print(registry.client.base_uri)
    registry.read_registry()