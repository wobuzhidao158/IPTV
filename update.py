import requests
import os

# 本地自己的源（必须放仓库根目录：直播源.txt）
LOCAL_FILE = "直播源.txt"
# 输出最终 m3u
OUTPUT_FILE = "iptv.m3u"
# 网络补充源（你自己那个仓库）
NET_URL = "https://raw.githubusercontent.com/wobuzhidao158/IPTV/main/iptv.m3u"

# ----------------------
# 1. 读取本地直播源.txt
# ----------------------
local_channels = []
if os.path.exists(LOCAL_FILE):
    with open(LOCAL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "," in line:
                parts = line.split(",", 1)
                name = parts[0].strip()
                url = parts[1].strip()
                if url.startswith("http"):
                    local_channels.append((name, url))

# ----------------------
# 2. 抓取网络源补充
# ----------------------
net_channels = []
try:
    resp = requests.get(NET_URL, timeout=10)
    lines = resp.text.splitlines()
    i = 0
    while i < len(lines):
        l = lines[i].strip()
        if l.startswith("#EXTINF"):
            name = l.split(",")[-1].strip()
            if i + 1 < len(lines):
                url = lines[i+1].strip()
                if url.startswith("http"):
                    net_channels.append((name, url))
                    i += 2
                    continue
        i += 1
except:
    pass

# ----------------------
# 3. 合并：本地优先 + 网络补充
# ----------------------
all_channels = []
exist_names = set()

# 先加本地
for name, url in local_channels:
    if name not in exist_names:
        all_channels.append((name, url))
        exist_names.add(name)

# 再加网络
for name, url in net_channels:
    if name not in exist_names:
        all_channels.append((name, url))
        exist_names.add(name)

# ----------------------
# 4. 输出标准 m3u
# ----------------------
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write('#EXTM3U x-tvg-url="https://epg.112114.xyz/epg.xml.gz"\n')
    for name, url in all_channels:
        f.write(f'#EXTINF:-1,{name}\n{url}\n')

print(f"✅ 本地：{len(local_channels)} 个")
print(f"✅ 网络：{len(net_channels)} 个")
print(f"✅ 最终：{len(all_channels)} 个")
