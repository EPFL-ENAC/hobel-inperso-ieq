"""Load the configuration and read the environment variables."""

import os

from dotenv import load_dotenv

from inperso.utils import load_yaml, update_dict_nested

load_dotenv()


def load_config() -> dict:
    """Load the configuration file and return it as a dictionary."""

    module_path = os.path.dirname(__file__)
    config_path = os.path.join(module_path, "config.yaml")

    return load_yaml(config_path)


def add_env_variables_to_config(config: dict) -> dict:
    """Add environment variables to the configuration dictionary.

    The queried environment variables are defined in the "from_env" key of the original dictionary.
    """

    from_env = config.pop("from_env", {})
    from_env = read_env_variables(from_env)
    config = update_dict_nested(config, from_env)

    return config


def read_env_variables(entry: dict) -> dict:
    """Replace the end values of the dictionary with the corresponding environment variables."""

    new_entry = entry.copy()

    for key, value in new_entry.items():
        if isinstance(value, dict):
            new_entry[key] = read_env_variables(value)
        else:
            new_entry[key] = os.getenv(value, "")

    return new_entry


config = load_config()
config = add_env_variables_to_config(config)


# Database configuration
db = config["db"]

# APIs configuration
airly = config["airly"]
airthings = config["airthings"]
qualtrics = config["qualtrics"]
uhoo = config["uhoo"]

# Field names synonyms
field_synonyms = config["field_synonyms"]
