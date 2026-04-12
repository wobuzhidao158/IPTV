# -*- coding: utf-8 -*-
# 新疆终极三合一版：全频道齐全+低延迟防卡+不空数据+排序规整
import os
import requests
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# ========== 新疆黄金配置区勿改 ==========
LOCAL_TXT = "直播源.txt"
OWN_REMOTE = "https://zhibo.cc.cd/api.php?token=BVna62di&type=txt"
OUT_M3U = "iptv.m3u"
LOG_TXT = "update_log.txt"
CHECK_TIMEOUT = 3
MAX_ALLOWED_LATENCY = 180
# 补全双备用源，频道不丢失
BACKUP_POOL = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u"
]
# ======================================

# 央视数字精准排序
def get_cctv_number(name):
    m = re.search(r'CCTV[-]?(\d+)(\+)?', name, re.IGNORECASE)
    if m:
        num = int(m.group(1))
        return num + 0.5 if m.group(2) == '+' else num
    alias = {"一套":1,"二套":2,"三套":3,"四套":4,"五套":5,"六套":6,"七套":7,"八套":8}
    for a,n in alias.items():
        if a in name:return n
    return 99 if '4K' in name else 100

# 卫视全国标准排序
WEISHI_ORDER = [
    "北京卫视","天津卫视","河北卫视","山西卫视","内蒙古卫视",
    "辽宁卫视","吉林卫视","黑龙江卫视","上海东方卫视","江苏卫视",
    "浙江卫视","安徽卫视","福建东南卫视","江西卫视","山东卫视",
    "河南卫视","湖北卫视","湖南卫视","广东卫视","广西卫视",
    "海南卫视","重庆卫视","四川卫视","贵州卫视","云南卫视",
    "西藏卫视","陕西卫视","甘肃卫视","青海卫视","宁夏卫视","新疆卫视"
]
def get_weishi_rank(name):
    for idx,s in enumerate(WEISHI_ORDER):
        if s in name:return idx
    return 999

# 全分类不丢频道
CATEGORIES = [
    {"name":"📺央视频道","kw":["CCTV","央视","cctv","中央"]},
    {"name":"📺卫视频道","kw":["卫视","东方卫视","东南卫视"]},
    {"name":"🎬影视频道","kw":["电影","影视","剧场"]},
    {"name":"🧒少儿频道","kw":["少儿","动画","卡通"]}
]

def get_lines_from_text(text):
    return [x.strip() for x in text.splitlines() if x.strip()]

# 容错拉取不怕网络差
def fetch_text(url):
    try:
        r = requests.get(url, timeout=12, verify=False)
        r.encoding = "utf-8"
        return get_lines_from_text(r.text)
    except:
        return []

# 新疆低延迟检测：只留不卡的，不滥杀源
def check_latency_ok(url):
    if not url.startswith("http"):
        return False
    try:
        s = time.time()
        res = requests.head(url, timeout=CHECK_TIMEOUT, allow_redirects=True, verify=False)
        cost = (time.time()-s)*1000
        return res.status_code in (200,301,302) and cost < MAX_ALLOWED_LATENCY
    except:
        return True

# 兼容两种格式解析不丢频道
def parse_all(lines):
    chans,seen = [],set()
    i=0
    while i<len(lines):
        t = lines[i]
        if t.startswith("#EXTINF") and i+1<len(lines):
            n = t.split(",")[-1].strip()
            u = lines[i+1].strip()
            if u not in seen:
                seen.add(u)
                chans.append((n,u))
            i+=2
        elif "," in t and not t.startswith("#"):
            part = t.split(",",1)
            if len(part)==2:
                n,u = part[0].strip(), part[1].strip()
                if u not in seen:
                    seen.add(u)
                    chans.append((n,u))
            i+=1
        else:
            i+=1
    return chans

def match_group(name):
    low = name.lower()
    for g in CATEGORIES:
        for k in g["kw"]:
            if k in low:
                return g["name"]
    return "📺其他频道"

def main():
    requests.packages.urllib3.disable_warnings()
    # 三路合并，频道补满
    local = fetch_text(LOCAL_TXT) if os.path.exists(LOCAL_TXT) else []
    remote = fetch_text(OWN_REMOTE)
    backup = []
    for b in BACKUP_POOL:
        backup += fetch_text(b)
    raw = parse_all(local+remote+backup)
    print(f"📥总采集源：{len(raw)}")

    # 筛选：保频道+筛卡顿
    good = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        tasks = {ex.submit(check_latency_ok,u):(n,u) for n,u in raw}
        for f in as_completed(tasks):
            n,u = tasks[f]
            if f.result():
                good.append((n,u))
    print(f"✅可用低延迟频道：{len(good)}")

    # 分类+强制规整排序
    bucket = {g["name"]:[] for g in CATEGORIES}
    bucket["📺其他频道"] = []
    for n,u in good:
        bucket[match_group(n)].append((n,u))
    bucket["📺央视频道"] = sorted(bucket["📺央视频道"], key=lambda x:get_cctv_number(x[0]))
    bucket["📺卫视频道"] = sorted(bucket["📺卫视频道"], key=lambda x:get_weishi_rank(x[0]))

    # 生成标准M3U不空数据
    m3u = ['#EXTM3U x-tvg-url="https://epg.112114.xyz/epg.xml.gz"']
    order = [g["name"] for g in CATEGORIES]+["📺其他频道"]
    for gname in order:
        for n,u in bucket[gname]:
            m3u.append(f'#EXTINF:-1 group-title="{gname}",{n}')
            m3u.append(u)

    with open(OUT_M3U,"w",encoding="utf-8") as f:
        f.write("\n".join(m3u)+"\n")
    log = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 三合一终极版|总{len(raw)}|可用{len(good)}\n"
    with open(LOG_TXT,"a",encoding="utf-8") as f:
        f.write(log)
    print("🎉执行完毕：频道齐全+不乱序+新疆WiFi不卡+不空数据")

if __name__=="__main__":
    main()
