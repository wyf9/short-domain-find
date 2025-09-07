# coding: utf-8

from config import config as c

with open('suffixs.txt', 'r', encoding='utf-8') as f:
    lines = f.read()

suffixs_orig = lines.split('\n')
for s in suffixs_orig:
    if s.startswith('#') or (not s):
        suffixs_orig.remove(s)

suffixs = []
for s in suffixs_orig:
    if len(s) <= c.max_length:
        suffixs.append(s.lower())