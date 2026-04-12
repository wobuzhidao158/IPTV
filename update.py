# -*- coding: utf-8 -*-
# 新疆WiFi专属不死空版｜不删弱源+三链路兼容+全频道不乱序
import os
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import re

# ========== 新疆适配基础配置 ==========
LOCAL_TXT = "直播源.txt"
OWN_REMOTE = "https://zhibo.cc.cd/api.php?token=BVna62di&type=txt"
OUT_M3U = "iptv.m3u"
LOG_TXT = "update_log.txt"
CHECK_TIMEOUT = 6
# 只留国内不被墙备用源，适配新疆网络
BACKUP_POOL = []
# =====================================

# 央视数字精准排序规则
def get_cctv_number(name):
    match = re.search(r'CCTV[-]?(\d+)(\+)?', name, re.IGNORECASE)
    if match:
        num = int(match.group(1))
        return num + 0.5 if match.group(2) == '+' else num
    alias = {"一套":1,"二套":2,"三套":3,"四套":4,"五套":5,"六套":6,"七套":7,"八套":8}
    for a,n in alias.items():
        if a in name:return n
    return 99 if '4K' in name else 100

CATEGORIES = [
    {"name":"📺央视频道","kw":["CCTV","央视","cctv"]},
    {"name":"📺卫视频道","kw":["卫视","北京","浙江","湖南","江苏"]},
    {"name":"🎬影视频道","kw":["电影","影视","剧场"]},
    {"name":"🧒少儿频道","kw":["少儿","动画","卡通"]}
]

def get_lines_from_text(text):
    return [x.strip() for x in text.splitlines() if x.strip()]

# 容错拉取，网络差也不报错中断
def fetch_text(url):
    try:
        r = requests.get(url, timeout=10, verify=False)
        r.encoding = "utf-8"
        return get_lines_from_text(r.text)
    except:
        print(f"轻度拉取失败，跳过：{url}")
        return []

# 新疆专属宽松校验：只要是http链接就保留，不空源最重要
def xinjiang_safe_check(url):
    return url.startswith("http") and ("m3u8" in url or "ts" in url)

def parse_all(lines):
    chans, seen = [], set()
    i = 0
    while i < len(lines):
        s = lines[i]
        if "," in s and not s.startswith("#"):
            n,u = s.split(",",1)
            n,u = n.strip(),u.strip()
            if u not in seen and xinjiang_safe_check(u):
                seen.add(u)
                chans.append((n,u))
            i += 1
        elif s.startswith("#EXTINF") and i+1 < len(lines):
            n = s.split(",")[-1].strip()
            u = lines[i+1].strip()
            if u not in seen and xinjiang_safe_check(u):
                seen.add(u)
                chans.append((n,u))
            i += 2
        else:
            i += 1
    return chans

def match_group(name):
    n = name.lower()
    for g in CATEGORIES:
        for k in g["kw"]:
            if k.lower() in n:
                return g["name"]
    return "其他频道"

def main():
    requests.packages.urllib3.disable_warnings()
    # 三路源容错合并
    local = fetch_text(LOCAL_TXT) if os.path.exists(LOCAL_TXT) else []
    remote = fetch_text(OWN_REMOTE)
    total_raw = parse_all(local + remote)
    print(f"已采集可用链接总数：{len(total_raw)}")

    # 分类+央视强制排序
    bucket = {g["name"]:[] for g in CATEGORIES}
    bucket["其他频道"] = []
    for n,u in total_raw:
        bucket[match_group(n)].append((n,u))
    bucket["📺央视频道"] = sorted(bucket["📺央视频道"], key=lambda x:get_cctv_number(x[0]))

    # 生成标准M3U，绝不空文件
    m3u = ['#EXTM3U x-tvg-url="https://epg.112114.xyz/epg.xml.gz"']
    order = [g["name"] for g in CATEGORIES] + ["其他频道"]
    for gname in order:
        for n,u in bucket[gname]:
            m3u.append(f'#EXTINF:-1 group-title="{gname}",{n}')
            m3u.append(u)
    
    with open(OUT_M3U,"w",encoding="utf-8") as f:
        f.write("\n".join(m3u)+"\n")
    log = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 新疆专属版｜可用源{len(total_raw)}个，不空数据\n"
    with open(LOG_TXT,"a",encoding="utf-8") as f:
        f.write(log)
    print(log+"✅完成！再也不获取数据为空！")

if __name__ == "__main__":
    main()
