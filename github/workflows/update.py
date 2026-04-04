import requests

# http://zhibo.cc.cd/api.php?token=OawLE8oN&type=m3u
SOURCE_URL = "https://example.com/iptv.m3u"
# 直播源（ http://zhibo.cc.cd/api.php?token=OawLE8oN&type=m3u）
OUTPUT_FILE = "iptv.m3u"

# 拉取内容
headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(直播源, headers=headers, timeout=15)
response.encoding = "utf-8"

# 保存到文件
with open(http://zhibo.cc.cd/api.php?token=OawLE8oN&type=m3u  , "w", encoding="utf-8") as f:
    f.write(response.text)

print("更新完成，已保存到", OUTPUT_FILE)
