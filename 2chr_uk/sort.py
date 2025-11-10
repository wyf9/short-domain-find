#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立脚本：读取 2char_uk_domains.csv
筛选：未注册 + 即将过期/暂停
按剩余天数升序排序
输出：Markdown 表格
"""

import csv
from datetime import datetime
from pathlib import Path

# === 配置 ===
INPUT_CSV = "2char_uk_domains.csv"   # 输入文件
OUTPUT_MD = "2char_uk_priority.md"   # 输出 Markdown
CURRENT_DATE = datetime.now()

# 优先状态
PRIORITY_STATUS = ["available", "suspended", "expiring_soon", "expired"]
STATUS_LABEL = {
    "available": "可注册",
    "suspended": "已暂停",
    "expiring_soon": "即将到期",
    "expired": "已过期",
    "registered": "已注册",
    "parse_error": "解析错误"
}

# === 主函数 ===


def main():
    input_path = Path(INPUT_CSV)
    if not input_path.exists():
        print(f"错误：找不到文件 {INPUT_CSV}")
        return

    domains = []
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            domain = row["域名"].strip()
            status = row["状态"].strip()
            expiry_str = row["过期日期"].strip()
            days_left_str = row["剩余天数"].strip()
            note = row["备注"].strip()

            # 转换剩余天数
            try:
                days_left = int(days_left_str) if days_left_str and days_left_str != "None" else None
            except:
                days_left = None

            # 仅保留优先域名
            if status not in ["available", "suspended", "expiring_soon"]:
                continue

            domains.append({
                "domain": domain,
                "status": status,
                "status_cn": STATUS_LABEL.get(status, status),
                "expiry": expiry_str,
                "days_left": days_left,
                "note": note
            })

    # === 排序逻辑 ===
    def sort_key(d):
        status = d["status"]
        days = d["days_left"]

        # 1. 状态优先级
        status_rank = PRIORITY_STATUS.index(status) if status in PRIORITY_STATUS else 99

        # 2. 可用域名排最前
        if status == "available":
            return (0, 0)

        # 3. 已暂停/过期
        if status in ["suspended", "expired"]:
            return (1, 0)

        # 4. 即将到期：按天数升序
        if days is not None:
            return (2, max(days, -365))  # 负数也支持
        return (2, 999)

    domains.sort(key=sort_key)

    # === 生成 Markdown ===
    md_lines = []
    md_lines.append("# 二字符 .uk 域名优先列表")
    md_lines.append(f"*生成时间：{CURRENT_DATE.strftime('%Y-%m-%d %H:%M:%S')}*  \n")
    md_lines.append(f"共 **{len(domains)}** 个优质域名（未注册 + 即将释放）\n")

    if not domains:
        md_lines.append("> 暂无符合条件的域名。")
    else:
        md_lines.append("| 域名 | 状态 | 过期日期 | 剩余天数 | 备注 |")
        md_lines.append("|------|------|----------|----------|------|")
        for d in domains:
            days = f"**{d['days_left']}**" if d['days_left'] is not None else "-"
            if d['days_left'] is not None and d['days_left'] <= 7:
                days = f"**`{d['days_left']}`**"  # 高亮一周内
            md_lines.append(
                f"| {d['domain']} | {d['status_cn']} | {d['expiry']} | {days} | {d['note']} |"
            )

    # === 写入文件 ===
    output_path = Path(OUTPUT_MD)
    output_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"成功！Markdown 已保存至：{output_path}")

    # === 控制台预览 ===
    print("\n" + "="*60)
    print("预览（前10条）:")
    print("="*60)
    for line in md_lines[:15]:
        print(line)
    if len(md_lines) > 15:
        print("...")


if __name__ == "__main__":
    main()
