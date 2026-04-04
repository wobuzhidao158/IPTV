import requests

# http://zhibo.cc.cd/api.php?token=OawLE8oN&type=m3u
SOURCE_URL = "http://zhibo.cc.cd/api.php?token=0awLE8oN&type=m3u"
# 保存到仓库里的文件名，比如你叫iptv.m3u就填这个
OUTPUT_FILE = "http://zhibo.cc.cd/api.php?token=OawLE8oN&type=m3u"

# 拉取内容
headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(SOURCE_URL, headers=headers, timeout=15)
response.encoding = "utf-8"

# 保存到文件
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(response.text)

print("更新完成，已保存到", OUTPUT_FILE)
