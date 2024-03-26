import os

from inperso.utils import load_yaml, update_dict_nested


def load_config() -> dict:
    module_path = os.path.dirname(__file__)
    config_path = os.path.join(module_path, "config.yaml")

    return load_yaml(config_path)


def add_env_variables_to_config(config: dict) -> dict:
    from_env = config.pop("from_env", {})
    from_env = read_env_variables(from_env)
    config = update_dict_nested(config, from_env)

    return config


def read_env_variables(entry: dict) -> dict:
    for key, value in entry.items():
        if isinstance(value, dict):
            entry[key] = read_env_variables(value)
        else:
            entry[key] = os.getenv(value, "")

    return entry


config = load_config()
config = add_env_variables_to_config(config)
db = config["db"]
