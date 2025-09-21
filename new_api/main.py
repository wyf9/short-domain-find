import threading
import os
import string
import itertools
import time
import requests
import sys

# —— 补丁：屏蔽 DummyThread 相关 __del__ 异常 —— #
def _patch_del(cls_name):
    cls = getattr(threading, cls_name, None)
    if cls and hasattr(cls, "__del__"):
        orig = cls.__del__
        def safe_del(self):
            try:
                orig(self)
            except Exception:
                pass
        cls.__del__ = safe_del

_patch_del("_DummyThread")
_patch_del("_DeleteDummyThreadOnDel")
# atexit.register(threading._shutdown)  # Removed: _shutdown is not a public attribute

# —— 配置区 —— #
API_URL           = "https://v2.xxapi.cn/api/whois"  # 新的API接口
BACKUP_API_URL    = "https://api.whoiscx.com/whois/"  # 备用API接口
DELAY_SECONDS     = 2                  # 每次请求的延迟时间
MAX_RETRIES       = 2                  # 对失败的域名重试次数
OUTPUT_DIR        = "output"
INPUT_FILE        = os.path.join(OUTPUT_DIR, "input.txt")
UNREGISTERED_FILE = os.path.join(OUTPUT_DIR, "domain.txt")
ERROR_FILE        = os.path.join(OUTPUT_DIR, "error.txt")
# —— 配置结束 —— #
# —— 支持自定义域名后缀 —— #
suffix: str = input("请输入域名后缀：").replace(".", "")
DOMAIN_SUFFIX = "." + suffix  # 显式字符串拼接
# DOMAIN_SUFFIX = ".im"  # 可修改为其他后缀，如 ".com"、".cn" 等

def generate_domains() -> list[str]:
    """生成所有 [0-9a-z] 两字符组合 + 自定义后缀（共 36×36=1296 条）"""
    chars = string.digits + string.ascii_lowercase
    return [f"{a}{b}{DOMAIN_SUFFIX}" for a, b in itertools.product(chars, repeat=2)]

def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_domains(domains: list[str]):
    """把域名列表写入 input.txt"""
    with open(INPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(domains))

def query_whois(domain: str, timeout: float = 10.0):
    """
    调用 WHOIS 接口，返回 (HTTP 状态码, JSON 数据 或 错误字符串)
    GET https://v2.xxapi.cn/api/whois?domain=xxx
    """
    try:
        resp = requests.get(API_URL, params={"domain": domain}, timeout=timeout)
        resp.raise_for_status()
        return resp.status_code, resp.json()
    except Exception as e:
        return None, str(e)

def query_whois_backup(domain: str, timeout: float = 10.0):
    """
    调用备用 WHOIS 接口，返回 (HTTP 状态码, JSON 数据 或 错误字符串)
    GET https://api.whoiscx.com/whois/?domain=xxx&raw=1
    """
    try:
        resp = requests.get(BACKUP_API_URL, params={"domain": domain, "raw": 1}, timeout=timeout)
        resp.raise_for_status()
        return resp.status_code, resp.json()
    except Exception as e:
        return None, str(e)

def determine_status(http_status, payload) -> str:
    """
    根据返回的 raw 文本判断状态：
      - HTTP 200 且 payload.code==200:
          * data.Domain Name 为空或不存在 → "unregistered"
          * 否则 → "registered"
      - 其它情况 → "failed"
    """
    if http_status == 200 and isinstance(payload, dict) and payload.get("code") == 200:
        data = payload.get("data", {})
        domain_name = data.get("Domain Name", "")
        # 如果Domain Name为空，则认为未注册
        return "unregistered" if not domain_name else "registered"
    return "failed"

def determine_status_backup(http_status, payload) -> str:
    """
    根据备用API返回的 raw 文本判断状态：
      - HTTP 200 且 payload.status==1:
          * raw 字段以 "Not found" 开头 → "unregistered"
          * 否则 → "registered"
      - 其它情况 → "failed"
    """
    if http_status == 200 and isinstance(payload, dict) and payload.get("status") == 1:
        raw_text = payload["data"].get("raw", "")
        return "unregistered" if raw_text.startswith("Not found") else "registered"
    return "failed"

def check_domain(domain: str) -> dict:
    # 首先使用新API查询
    code, data = query_whois(domain)
    status = determine_status(code, data)
    
    # 如果新API查询失败，则使用备用API查询
    if status == "failed":
        code, data = query_whois_backup(domain)
        status = determine_status_backup(code, data)
    
    error = None
    if status == "failed":
        error = data if code is None else f"HTTP {code}: {data}"
    
    return {"domain": domain, "status": status, "http_code": code, "error": error}

def write_list_to_file(lst: list[str], path: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lst))

def main():
    try:
        ensure_output_dir()

        # 1. 生成 & 保存所有域名
        domains = generate_domains()
        save_domains(domains)
        total = len(domains)
        print(f"已生成 {total} 个 {DOMAIN_SUFFIX} 域名，写入 {INPUT_FILE}")
        time.sleep(1)

        # 2. 初始查询
        results = {}  # domain -> result dict
        print("开始初始查询…")
        
        # 域名查询循环
        for idx, d in enumerate(domains, start=1):
            res = check_domain(d)
            results[d] = res

            mark = {"registered":"🔴 已注册","unregistered":"🟢 未注册","failed":"🟡 查询失败"}[res["status"]]
            detail = f"(HTTP {res['http_code']})" + (f" 错误：{res['error']}" if res["error"] else "")
            percent = idx / total * 100
            print(f"{d}: {mark} {detail}   [{idx}/{total}, {percent:.2f}%]")

            time.sleep(DELAY_SECONDS)

        # 3. 写入初始失败列表
        error_domains = [d for d,r in results.items() if r["status"] == "failed"]
        write_list_to_file(error_domains, ERROR_FILE)
        print(f"\n初始查询完成，{len(error_domains)} 个域名失败，已写入 {ERROR_FILE}\n")

        # 4. 针对失败域名重试
        for attempt in range(1, MAX_RETRIES + 1):
            if not error_domains:
                break
            print(f"第 {attempt} 次重试，共 {len(error_domains)} 个域名…")
            new_errors = []
            for idx, d in enumerate(error_domains, start=1):
                res = check_domain(d)
                results[d] = res

                mark = {"registered":"🔴 已注册","unregistered":"🟢 未注册","failed":"🟡 查询失败"}[res["status"]]
                detail = f"(HTTP {res['http_code']})" + (f" 错误：{res['error']}" if res["error"] else "")
                percent = idx / len(error_domains) * 100
                print(f"重试 {attempt} - {d}: {mark} {detail}   [{idx}/{len(error_domains)}, {percent:.2f}%]")

                if res["status"] == "failed":
                    new_errors.append(d)
                time.sleep(DELAY_SECONDS)

            error_domains = new_errors
            write_list_to_file(error_domains, ERROR_FILE)
            print(f"重试 {attempt} 完毕，仍有 {len(error_domains)} 个失败，已更新 {ERROR_FILE}\n")

        # 5. 收集未注册并写入文件
        unreg = [d for d,r in results.items() if r["status"] == "unregistered"]
        write_list_to_file(unreg, UNREGISTERED_FILE)

        print(f"所有查询结束：未注册 {len(unreg)} 个（已写入 {UNREGISTERED_FILE}），"
              f"最终失败 {len(error_domains)} 个（见 {ERROR_FILE}）。")
    except KeyboardInterrupt:
        print("\n程序已终止。")
        sys.exit(0)
    except Exception as e:
        print(f"\n发生未知异常: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()