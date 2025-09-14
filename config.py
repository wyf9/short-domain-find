# coding: utf-8

from yaml import safe_load as load_yaml
from pydantic import BaseModel
import utils as u


class ConfigModel(BaseModel):
    apikey: str # api key
    numbers: bool = True # 是否包含数字
    output: str | None = None # 结果输出到指定文件 (markdown 格式)


try:
    with open('config.yaml', 'r', encoding='utf-8') as f:
        file = load_yaml(f)
except:
    file = {}

config = ConfigModel.model_validate(file)

if not config.apikey:
    u.error('Please provide your api key in config.yaml: `apikey: xxx`!')
    exit(1)
