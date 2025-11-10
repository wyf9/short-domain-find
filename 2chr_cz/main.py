#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
筛选二字 .cz 域名可用性
支持：未注册 > 即将过期 > 正常注册
"""

import subprocess
import re
import time
import csv
from datetime import datetime
from typing import List, Dict, Optional

# 配置
DELAY = 1.1  # CZ.NIC 建议查询间隔 >1s
OUTPUT_CSV = "2char_cz_domains.csv"
CHARS1 = "ijklmnopqrstuvwxyz"
CHARS2 = "0123456789abcdefghijklmnopqrstuvwxyz"

# 正则表达式
RE_DOMAIN = re.compile(r"domain:\s+([a-z0-9]{2}\.cz)", re.I)
RE_EXPIRE = re.compile(r"expire:\s+([\d]{2}\.[\d]{2}\.[\d]{4})", re.I)
RE_NO_ENTRY = re.compile(r"ERROR:101:\s*no entries found", re.I)
RE_NO_ENTRIES = re.compile(r"No entries found", re.I)


def parse_date_cz(date_str: str) -> Optional[datetime]:
    """解析 CZ 日期格式: 06.10.2026"""
    try:
        return datetime.strptime(date_str, "%d.%m.%Y")
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
    """分析 CZ.NIC whois 输出"""
    result = {
        "domain": domain,
        "status": "unknown",
        "expiry": None,
        "days_left": None,
        "note": ""
    }

    # 1. 未注册
    if RE_NO_ENTRY.search(output) or RE_NO_ENTRIES.search(output):
        result["status"] = "available"
        result["note"] = "未注册，可立即注册"
        return result

    # 2. 提取域名和过期日期
    domain_match = RE_DOMAIN.search(output)
    expiry_match = RE_EXPIRE.search(output)

    if not domain_match:
        result["status"] = "parse_error"
        result["note"] = "无法解析域名"
        return result

    expiry_date = None
    if expiry_match:
        expiry_str = expiry_match.group(1)
        expiry_date = parse_date_cz(expiry_str)
        result["expiry"] = expiry_str
        if expiry_date:
            days_left = (expiry_date - datetime.now()).days
            result["days_left"] = days_left

    # 3. 判断状态
    if expiry_date:
        days_left = (expiry_date - datetime.now()).days
        if days_left <= 0:
            result["status"] = "expired"
            result["note"] = f"已过期（{abs(days_left)}天前）"
        elif days_left <= 60:
            result["status"] = "expiring_soon"
            result["note"] = f"即将到期（{days_left}天）"
        else:
            result["status"] = "registered"
            result["note"] = f"正常注册，{days_left}天后到期"
    else:
        result["status"] = "registered"
        result["note"] = "已注册（无过期日期）"

    return result


def generate_2char_domains() -> List[str]:
    """生成所有二字符 .cz 域名（0-9, a-z）"""
    domains = []
    for c1 in CHARS1:
        for c2 in CHARS2:
            domains.append(f"{c1}{c2}.cz")
    return domains


def main():
    domains = generate_2char_domains()
    print(f"共生成 {len(domains)} 个二字符 .cz 域名，开始查询...")

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
            elif info["status"] in ["expiring_soon", "expired"]:
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

    print(f"\n即将过期/已过期: {len(expiring)} 个")
    for e in expiring:
        print(f"   {e['domain']} → {e['note']}")

    print(f"\n结果已保存至: {OUTPUT_CSV}")
    print("="*60)


if __name__ == "__main__":
    main()
