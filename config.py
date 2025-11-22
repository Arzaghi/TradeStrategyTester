import configparser
from pathlib import Path

class Config:
    _instance = None
    _config_file = Path(__file__).parent / "config.ini"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.reload()
        return cls._instance

    def reload(self):
        self._parser = configparser.ConfigParser()
        self._parser.read(self._config_file)

    def __getattr__(self, section):
        if section in self._parser:
            return ConfigSection(self._parser[section])
        return None
    
    def get(self, section, key=None, default=None):
        if section in self._parser:
            if key is None:
                return ConfigSection(self._parser[section])
            value = self._parser[section].get(key, default)
            return value.lower() if isinstance(value, str) else value
        return default.lower()
    
    def get_value(self, path: str, default : str) -> str:
        if "." not in path:
            return default.lower()

        section, key = path.split(".", 1)
        return self.get(section, key, default)


class ConfigSection:
    def __init__(self, section):
        self._section = section

    def __getattr__(self, key):
        value = self._section.get(key, None)
        return value.lower() if isinstance(value, str) else value

    def get(self, key=None, default=None):
        if key is None:
            return None
        value = self._section.get(key, default)
        return value.lower() if isinstance(value, str) else value

config = Config()
