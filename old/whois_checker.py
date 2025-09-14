import asyncio
import os
import string
import itertools
import aiohttp
import sys
from datetime import datetime

# —— 配置区 —— #
API_URL = "https://v2.xxapi.cn/api/whois"  # 新的 API 接口
BACKUP_API_URL = "https://api.whoiscx.com/whois/"  # 备用 API 接口
CONCURRENT_LIMIT = 50  # 并发请求限制
TIMEOUT = 10.0  # 每个请求的超时时间（秒）
MAX_RETRIES = 2  # 对失败的域名重试次数
OUTPUT_DIR = "output"
INPUT_FILE = os.path.join(OUTPUT_DIR, "input.txt")
UNREGISTERED_FILE = os.path.join(OUTPUT_DIR, "domain.txt")
ERROR_FILE = os.path.join(OUTPUT_DIR, "error.txt")

# —— 支持自定义域名后缀 —— #
suffix = input("请输入域名后缀：").replace(".", "")
DOMAIN_SUFFIX = "." + suffix  # 显式字符串拼接


def generate_domains() -> list[str]:
    """生成所有 [0-9a-z] 两字符组合 + 自定义后缀（共 36×36=1296 条）"""
    chars = string.digits + string.ascii_lowercase
    # chars = 'ab12'
    return [f"{a}{b}{DOMAIN_SUFFIX}" for a, b in itertools.product(chars, repeat=2)]


def ensure_output_dir():
    """确保输出目录存在"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_domains(domains: list[str]):
    """把域名列表写入 input.txt"""
    with open(INPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(domains))


async def query_whois(domain: str, session: aiohttp.ClientSession, timeout: float = TIMEOUT):
    """
    异步调用 WHOIS 接口，返回 (HTTP 状态码, JSON 数据 或 错误字符串)
    GET https://v2.xxapi.cn/api/whois?domain=xxx
    """
    try:
        async with session.get(API_URL, params={"domain": domain}, timeout=timeout) as resp:
            status = resp.status
            if status == 200:
                return status, await resp.json()
            return status, f"HTTP {status}"
    except Exception as e:
        return None, str(e)


async def query_whois_backup(domain: str, session: aiohttp.ClientSession, timeout: float = TIMEOUT):
    """
    异步调用备用 WHOIS 接口，返回 (HTTP 状态码, JSON 数据 或 错误字符串)
    GET https://api.whoiscx.com/whois/?domain=xxx&raw=1
    """
    try:
        async with session.get(BACKUP_API_URL, params={"domain": domain, "raw": 1}, timeout=timeout) as resp:
            status = resp.status
            if status == 200:
                return status, await resp.json()
            return status, f"HTTP {status}"
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
        return "unregistered" if not domain_name else "registered"
    return "failed"


def determine_status_backup(http_status, payload) -> str:
    """
    根据备用 API 返回的 raw 文本判断状态：
      - HTTP 200 且 payload.status==1:
          * raw 字段以 "Not found" 开头 → "unregistered"
          * 否则 → "registered"
      - 其它情况 → "failed"
    """
    if http_status == 200 and isinstance(payload, dict) and payload.get("status") == 1:
        raw_text = payload["data"].get("raw", "")
        return "unregistered" if raw_text.startswith("Not found") else "registered"
    return "failed"


async def check_domain(domain: str, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> dict:
    async with semaphore:
        # 首先使用新 API 查询
        code, data = await query_whois(domain, session)
        status = determine_status(code, data)

        # 如果新 API 查询失败，则使用备用 API 查询
        if status == "failed":
            code, data = await query_whois_backup(domain, session)
            status = determine_status_backup(code, data)

        error = None
        if status == "failed":
            error = data if code is None else f"HTTP {code}: {data}"

        return {"domain": domain, "status": status, "http_code": code, "error": error}


def write_list_to_file(lst: list[str], path: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lst))


async def main():
    try:
        ensure_output_dir()

        # 1. 生成 & 保存所有域名
        domains = generate_domains()
        save_domains(domains)
        total = len(domains)
        print(f"已生成 {total} 个 {DOMAIN_SUFFIX} 域名，写入 {INPUT_FILE}")

        # 2. 初始查询
        results = {}  # domain -> result dict
        print("开始初始查询…")

        async with aiohttp.ClientSession() as session:
            semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
            tasks = [check_domain(d, session, semaphore) for d in domains]
            completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, (d, res) in enumerate(zip(domains, completed_tasks), start=1):
                if isinstance(res, Exception):
                    res = {"domain": d, "status": "failed", "http_code": None, "error": str(res)}
                results[d] = res

                mark = {"registered": "🔴 已注册", "unregistered": "🟢 未注册", "failed": "🟡 查询失败"}[res["status"]]
                detail = f"(HTTP {res['http_code']})" + (f" 错误：{res['error']}" if res["error"] else "")
                percent = idx / total * 100
                print(f"{d}: {mark} {detail}   [{idx}/{total}, {percent:.2f}%]")

        # 3. 写入初始失败列表
        error_domains = [d for d, r in results.items() if r["status"] == "failed"]
        write_list_to_file(error_domains, ERROR_FILE)
        print(f"\n初始查询完成，{len(error_domains)} 个域名失败，已写入 {ERROR_FILE}\n")

        # 4. 针对失败域名重试
        for attempt in range(1, MAX_RETRIES + 1):
            if not error_domains:
                break
            print(f"第 {attempt} 次重试，共 {len(error_domains)} 个域名…")
            new_errors = []
            async with aiohttp.ClientSession() as session:
                semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
                tasks = [check_domain(d, session, semaphore) for d in error_domains]
                completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)

                for idx, (d, res) in enumerate(zip(error_domains, completed_tasks), start=1):
                    if isinstance(res, Exception):
                        res = {"domain": d, "status": "failed", "http_code": None, "error": str(res)}
                    results[d] = res

                    mark = {"registered": "🔴 已注册", "unregistered": "🟢 未注册", "failed": "🟡 查询失败"}[res["status"]]
                    detail = f"(HTTP {res['http_code']})" + (f" 错误：{res['error']}" if res["error"] else "")
                    percent = idx / len(error_domains) * 100
                    print(f"重试 {attempt} - {d}: {mark} {detail}   [{idx}/{len(error_domains)}, {percent:.2f}%]")

                    if res["status"] == "failed":
                        new_errors.append(d)

            error_domains = new_errors
            write_list_to_file(error_domains, ERROR_FILE)
            print(f"重试 {attempt} 完毕，仍有 {len(error_domains)} 个失败，已更新 {ERROR_FILE}\n")

        # 5. 收集未注册并写入文件
        unreg = [d for d, r in results.items() if r["status"] == "unregistered"]
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
    asyncio.run(main())
