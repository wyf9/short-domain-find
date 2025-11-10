#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
筛选二字 .uk 域名可用性
支持：未注册 > 即将过期/悬挂 > 正常注册
"""

import subprocess
import re
import time
import csv
from datetime import datetime
from typing import List, Dict, Optional

# 配置
DELAY = 1.05  # Nominet 建议查询间隔 >1s
OUTPUT_CSV = "2char_uk_domains.csv"
CURRENT_YEAR = 2025
CHARS_LVL1 = "ghijklmnopqrstuvwxyz"
CHARS_LVL2 = "0123456789abcdefghijklmnopqrstuvwxyz"

# 正则表达式
RE_DOMAIN = re.compile(r"Domain name:\s+([a-z0-9]{2}\.uk)", re.I)
RE_EXPIRY = re.compile(r"Expiry date:\s+([\d]{2}-[A-Za-z]{3}-[\d]{4})", re.I)
RE_STATUS = re.compile(r"Registration status:\s+(.+)", re.I)
RE_NO_MATCH = re.compile(r"No match for", re.I)
RE_SUSPENDED = re.compile(r"SUSPENDED", re.I)


def parse_date(date_str: str) -> Optional[datetime]:
    """解析日期如 02-Oct-2025"""
    try:
        return datetime.strptime(date_str, "%d-%b-%Y")
    except:
        return None


def run_whois(domain: str) -> str:
    """执行 whois 命令"""
    try:
        result = subprocess.run(
            ["whois", domain],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout
    except Exception as e:
        print(f"查询失败 {domain}: {e}")
        return ""


def analyze_whois(output: str, domain: str) -> Dict:
    """分析 whois 输出"""
    result = {
        "domain": domain,
        "status": "unknown",
        "expiry": None,
        "days_left": None,
        "note": ""
    }

    # 1. 未注册
    if RE_NO_MATCH.search(output):
        result["status"] = "available"
        result["note"] = "未注册，可立即抢注"
        return result

    # 2. 提取域名、过期日期、状态
    domain_match = RE_DOMAIN.search(output)
    expiry_match = RE_EXPIRY.search(output)
    status_match = RE_STATUS.search(output)

    if not domain_match:
        result["status"] = "parse_error"
        result["note"] = "无法解析域名"
        return result

    expiry_date = None
    if expiry_match:
        expiry_str = expiry_match.group(1)
        expiry_date = parse_date(expiry_str)
        result["expiry"] = expiry_str
        if expiry_date:
            days_left = (expiry_date - datetime.now()).days
            result["days_left"] = days_left

    status_line = status_match.group(1) if status_match else ""

    # 3. 判断状态
    if RE_SUSPENDED.search(output):
        result["status"] = "suspended"
        result["note"] = "已暂停，可能即将删除"
    elif "Renewal required" in status_line:
        if expiry_date and (expiry_date - datetime.now()).days <= 60:
            result["status"] = "expiring_soon"
            result["note"] = f"即将到期（{result['days_left']}天）"
        else:
            result["status"] = "renewal_required"
            result["note"] = "需续费但未到期"
    elif "Registered until expiry date" in status_line:
        if expiry_date and (expiry_date - datetime.now()).days <= 90:
            result["status"] = "expiring_soon"
            result["note"] = f"即将到期（{result['days_left']}天）"
        else:
            result["status"] = "registered"
            result["note"] = "正常注册"
    else:
        result["status"] = "registered"
        result["note"] = "状态未知但已注册"

    return result


def generate_2char_domains() -> List[str]:
    """生成所有二字符 .uk 域名（0-9, a-z）"""
    domains = []
    for c1 in CHARS_LVL1:
        for c2 in CHARS_LVL2:
            domains.append(f"{c1}{c2}.uk")
    return domains


def main():
    domains = generate_2char_domains()
    print(f"共生成 {len(domains)} 个二字符 .uk 域名，开始查询...")

    results = []
    available = []
    expiring = []

    with open(OUTPUT_CSV, "a+", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["域名", "状态", "过期日期", "剩余天数", "备注"])

        for i, domain in enumerate(domains):
            print(f"\r[{i+1}/{len(domains)}] 查询 {domain}...", end="", flush=True)

            output = run_whois(domain)
            info = analyze_whois(output, domain)

            # 分类
            if info["status"] == "available":
                available.append(info)
                print(f"\n[可注册] {domain}")
            elif info["status"] in ["expiring_soon", "suspended"]:
                expiring.append(info)
                print(f"\n[即将过期] {domain} → {info['note']}")

            results.append(info)
            writer.writerow([
                info["domain"],
                info["status"],
                info["expiry"] or "",
                info["days_left"] if info["days_left"] is not None else "",
                info["note"]
            ])

            time.sleep(DELAY)  # 避免被封

    # 总结
    print("\n\n" + "="*60)
    print("查询完成！")
    print(f"未注册域名: {len(available)} 个")
    for a in available[:10]:
        print(f"   {a['domain']}")
    if len(available) > 10:
        print(f"   ... 还有 {len(available)-10} 个")

    print(f"\n即将过期/暂停: {len(expiring)} 个")
    for e in expiring:
        print(f"   {e['domain']} → {e['note']}")

    print(f"\n结果已保存至: {OUTPUT_CSV}")
    print("="*60)


if __name__ == "__main__":
    main()
