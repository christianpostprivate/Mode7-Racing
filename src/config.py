import shutil
from os import path
import tomlkit


class Config:
    def __init__(self, config_file, example_file):
        self.config_file = config_file
        self.example_file = example_file
        self.load()

    def load(self):
        # create user config from example on first run
        if not path.exists(self.config_file):
            shutil.copy(self.example_file, self.config_file)
        with open(self.config_file, "r", encoding="utf-8") as f:
            self._data = tomlkit.load(f)

    def save(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            tomlkit.dump(self._data, f)

    def _parent(self, key_path):
        *parents, key = key_path.split(".")
        node = self._data
        for part in parents:
            node = node[part]  # KeyError if missing
        return node, key

    def __getitem__(self, key_path):
        node, key = self._parent(key_path)
        return node[key]

    def __setitem__(self, key_path, value):
        node, key = self._parent(key_path)
        if key not in node:
            raise KeyError(f"Unknown config key '{key_path}'")
        old = node[key]
        old_type = type(old.unwrap() if hasattr(old, "unwrap") else old)
        if old_type is not type(value):
            raise TypeError(f"'{key_path}' expects {old_type.__name__}, "
                            f"got {type(value).__name__}")
        node[key] = value