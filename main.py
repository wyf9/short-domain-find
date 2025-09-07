from config import config as c
from utils import *
import asyncio

async def main():
    suffs = await get_suffixs(c.max_length)
    print(f'Got suffixs: {suffs}')

if __name__ == '__main__':
    asyncio.run(main())
