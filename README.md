# short-domain-find

## new-api

文件: ![new_api/main.py](./new_api/main.py)

依赖: ![`requests`](./new_api/pyproject.toml)

配置:

```py
API_URL           = "https://v2.xxapi.cn/api/whois"  # 新的API接口
BACKUP_API_URL    = "https://api.whoiscx.com/whois/"  # 备用API接口
DELAY_SECONDS     = 2                  # 每次请求的延迟时间
MAX_RETRIES       = 2                  # 对失败的域名重试次数
OUTPUT_DIR        = "output"
INPUT_FILE        = os.path.join(OUTPUT_DIR, "input.txt")
UNREGISTERED_FILE = os.path.join(OUTPUT_DIR, "domain.txt")
ERROR_FILE        = os.path.join(OUTPUT_DIR, "error.txt")
```

## 旧版本

## [old-bulk-whois-api](./old-bulk-whois-api/)

因为沙比 [bulk-whois-api](https://whois.whoisxmlapi.com/bulk-api/documentation/getting-whois-records) 的查询量竟然是按域名而不是请求算的, 不再维护, 自行寻找用法.

## [old](./old/)

不维护, 自行寻找用法.

- `check_short_prefix.py`: 使用 `whois` 命令查询指定后缀的可用域名列表 (不建议使用, 检测不完全)
- `download-suffix-list.sh`: 下载后缀列表
- `get_suffixs.py`: 筛选指定长度后缀
- `whois_checker`: (未测试) 使用三方 api 查询