import subprocess
from colorama import Fore, Style
from typing import Any
from time import asctime

def info(*log: Any):
    print(f'[{asctime()}] {Fore.GREEN}{" ".join(str(l) for l in log)}{Style.RESET_ALL}')


def warn(*log: Any):
    print(f'[{asctime()}] {Fore.YELLOW}{" ".join(str(l) for l in log)}{Style.RESET_ALL}')

def error(*log: Any):
    print(f'[{asctime()}] {Fore.RED}{" ".join(str(l) for l in log)}{Style.RESET_ALL}')

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
    code, ret = subprocess.getstatusoutput(f'whois {domain}')
    if code: # != 0
        warn(f'[check_available] {domain} error: ({code}) {ret} -> None')
        return None
    else:
        ret = ret.lower()
        if 'can\'t find' in ret or 'not found' in ret or 'not exist' in ret:
            info(f'[check_available] {domain} not found -> True')
            return True
        else:
            info(f'[check_available] {domain} (maybe) exists -> False')
            return False