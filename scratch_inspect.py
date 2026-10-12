import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
import httpx
import re

r = httpx.get("https://cdn.tgmrkt.io/js/app-shared-Da7-k-YS.js")
text = r.text

idx = text.find('GIFT_DETAILS')
while idx != -1:
    print(text[max(0, idx - 40):min(len(text), idx + 100)])
    print("-" * 30)
    idx = text.find('GIFT_DETAILS', idx + 1)
