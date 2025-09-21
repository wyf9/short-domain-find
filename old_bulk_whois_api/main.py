# coding: utf-8

from sys import argv
import itertools
from datetime import datetime
from typing import Callable
from os import makedirs

import bulkwhoisapi

from config import config as c
import utils as u

CHARS = 'abcdefghijklmnopqrstuvwxyz'
NUMBERS = '0123456789'


def proceed():
    try:
        input('按 Enter 以继续操作... ')
    except (KeyboardInterrupt, EOFError):
        print()
        exit(2)


class Result:
    string = ''

    def __init__(self, suffix: str, length: int):
        self.suffix = suffix
        self.length = length

    def info(self, *logs):
        s = ' '.join(str(l) for l in logs)
        u.info(s)
        self.string += s + '\n'

    def warn(self, *logs):
        s = ' '.join(str(l) for l in logs)
        u.warn(s)
        self.string += s + '\n'

    def error(self, *logs):
        s = ' '.join(str(l) for l in logs)
        u.error(s)
        self.string += s + '\n'

    def save(self):
        makedirs('output', exist_ok=True)
        with open(u.get_path(f'output/domains-{self.suffix}-{self.length}.md'), 'w', encoding='utf-8') as f:
            f.write(self.string)


def parse_results(lst: list[bulkwhoisapi.BulkWhoisRecord], suffix: str, length: int, perf: Callable):
    r = Result(suffix, length)
    r.info(f'* 时间: **{datetime.now()}**')
    r.info(f'* 后缀: **{suffix}**')
    r.info(f'* 长度: **{length}**')
    r.info(f'* 域名结果 (总共 **{len(lst)}**)')
    for rec in lst:
        if rec.domain_status == 'N':
            r.error(f'  - **`{rec.domain_name}`**: **不可用**')
        elif rec.domain_status == 'I':
            r.info(f'  - **`{rec.domain_name}`**: **可用**')
        else:
            r.warn(f'  - **`{rec.domain_name}`**: **未知**')
    r.info(f'* 用时: **{perf()}**ms')
    r.save()
    exit(0)

def new_req():
    perf = u.perf_counter()
    try:
        suffix = argv[1]
        length = int(argv[2])
    except:
        u.error('使用: main.py <后缀> <长度 (必须为整数!)>')
        exit(1)

    domains = [f"{''.join(combo)}.{suffix}" for combo in itertools.product(CHARS + NUMBERS if c.numbers else CHARS, repeat=length)]

    u.info(f'域名数: {len(domains)} (从 {domains[0]} 到 {domains[-1]}), 是否继续?')
    proceed()

    client = bulkwhoisapi.Client(api_key=c.apikey)
    req = client.create_request(domains=domains)

    reqid = req.request_id

    result = client.get_records(
        request_id=reqid,
        max_records=len(domains)
    )

    records: list[bulkwhoisapi.BulkWhoisRecord] = result.whois_records

    parse_results(records, suffix, length, perf)

def main():
    if len(argv) == 3:
        # new request
        new_req()
    else:
        # show history (undone)
        raise NotImplementedError('历史记录功能还没做')


if __name__ == '__main__':
    main()
