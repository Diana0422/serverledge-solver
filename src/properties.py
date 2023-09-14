from jproperties import Properties


# loads the config.properties file
class Props:
    ServerPort: int

    def __init__(self):
        configs = Properties()
        with open('config.properties', 'rb') as config_file:
            configs.load(config_file, "utf-8")
            self.ServerPort = configs.get("ServerPort")[0]