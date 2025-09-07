# coding: utf-8

from yaml import safe_load as load_yaml
from pydantic import BaseModel


class ConfigModel(BaseModel):
    max_length: int = 3


try:
    with open('config.yaml', 'r', encoding='utf-8') as f:
        file = load_yaml(f)
except:
    file = {}

config = ConfigModel.model_validate(file)
