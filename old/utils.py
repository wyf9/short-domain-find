import asyncio
from colorama import Fore, Style
from typing import Any
from time import perf_counter as _perf_counter


def info(*log: Any):
    print(f'{Fore.GREEN}{" ".join(str(l) for l in log)}{Style.RESET_ALL}')


def warn(*log: Any):
    print(f'{Fore.YELLOW}{" ".join(str(l) for l in log)}{Style.RESET_ALL}')


def error(*log: Any):
    print(f'{Fore.RED}{" ".join(str(l) for l in log)}{Style.RESET_ALL}')


async def get_suffixs(max_length: int) -> list[str]:
    with open('suffixs.txt', 'r', encoding='utf-8') as f:
        lines = f.read()

    suffixs_orig = lines.split('\n')
    for s in suffixs_orig:
        if s.startswith('#') or (not s):
            suffixs_orig.remove(s)

    suffixs = []
    for s in suffixs_orig:
        if len(s) <= max_length:
            suffixs.append(s.lower())

    return suffixs


async def check_available(domain: str) -> bool | None:
    '''
    success: bool (available or not)
    failed: None (execute err / no whois server)
    '''
    try:
        # 异步运行 whois 命令
        process = await asyncio.create_subprocess_exec(
            'whois', domain,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        # 异步等待命令输出
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            warn(f'[check_available : {domain}] error: ({process.returncode}) {stderr.decode()} -> None')
            return None

        # 检查输出
        output = stdout.decode().lower()
        if "can't find" in output or 'not found' in output or 'not exist' in output or 'Status: free' in output:
            info(f'[check_available : {domain}] not found -> True')
            return True
        else:
            info(f'[check_available : {domain}] (maybe) exists -> False')
            return False

    except Exception as e:
        warn(f'[check_available : {domain}] exception: {e} -> None')
        return None


def perf_counter():
    '''
    获取一个性能计数器, 执行返回函数来结束计时, 并返回保留两位小数的毫秒值
    '''
    start = _perf_counter()
    return lambda: round((_perf_counter() - start)*1000, 2)
