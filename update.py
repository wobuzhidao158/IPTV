# update.py
import requests

# 1. 从公开地址拉取最新源（替换成你要抓取的地址）
url = "https://example.com/iptv.m3u"
response = requests.get(url, timeout=10)
response.encoding = 'utf-8'

# 2. 保存到你的仓库文件里（替换成你自己的文件名，比如 main.m3u）
with open("main.m3u", "w", encoding="utf-8") as f:
    f.write(response.text)
