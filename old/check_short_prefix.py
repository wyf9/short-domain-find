# coding: utf-8

from sys import argv
import asyncio
import itertools
from datetime import datetime

from utils import *
from config import config as c

# 定义字符集
if c.contain_number:
    CHARS = 'qwertyuiopasdfghjklzxcvbnm1234567890'  # 完整字母表
else:
    CHARS = 'qwertyuiopasdfghjklzxcvbnm'  # 完整字母表
# CHARS = 'qwer'
THREADS = c.threads  # 增加并发数量，异步调用允许更高的并发


async def check_domain_with_semaphore(
        domain: str,
        semaphore: asyncio.Semaphore
):
    async with semaphore:
        result = await check_available(domain=domain)
        if result:
            with open('available_prefixes.yaml', 'a', encoding='utf-8') as f:
                f.write(f'- {domain}\n')


async def main():
    try:
        suffix = argv[1].lstrip('.')  # 支持 ".com" 或 "com" 格式
        assert suffix
    except (IndexError, AssertionError):
        error('Please provide a domain suffix at param #1!')
        exit(1)

    # 写入开始时间
    with open('available_prefixes.yaml', 'w', encoding='utf-8') as f:
        f.write(f'# Start: {datetime.now()}\n')

    # 生成二字符组合
    two_char_combinations = [''.join(combo) for combo in itertools.product(CHARS, repeat=2)]
    semaphore = asyncio.Semaphore(THREADS)
    tasks = [check_domain_with_semaphore(f"{prefix}.{suffix}", semaphore) for prefix in two_char_combinations]
    await asyncio.gather(*tasks, return_exceptions=True)

    # 写入结束时间
    with open('available_prefixes.yaml', 'a', encoding='utf-8') as f:
        f.write(f'# End: {datetime.now()}\n')

if __name__ == '__main__':
    asyncio.run(main())
