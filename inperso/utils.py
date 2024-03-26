import yaml


def load_yaml(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def update_dict_nested(target: dict, update: dict) -> dict:
    for key, value in update.items():
        if isinstance(value, dict):
            current = target.get(key, {})
            target[key] = update_dict_nested(current, value)
        else:
            target[key] = value

    return target
