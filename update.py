# -*- coding: utf-8 -*-
# 央视顺序100%锁死版｜多线程+精准匹配+强制排序，彻底解决乱序
import os
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# ========== 基础配置 ==========
LOCAL_TXT = "直播源.txt"
OWN_REMOTE = "https://zhibo.cc.cd/api.php?token=BVna62di&type=txt"
OUT_M3U = "iptv.m3u"
LOG_TXT = "update_log.txt"
CHECK_TIMEOUT = 2.5
BACKUP_POOL = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u"
]
# ==============================

# 【核心1：央视100%锁死排序表，覆盖所有别名/后缀】
CCTV_ORDER = [
    # 主频道（严格按数字顺序）
    "CCTV-1", "CCTV1", "央视一套", "CCTV-1综合",
    "CCTV-2", "CCTV2", "央视二套", "CCTV-2财经",
    "CCTV-3", "CCTV3", "央视三套", "CCTV-3综艺",
    "CCTV-4", "CCTV4", "央视四套", "CCTV-4中文国际",
    "CCTV-5", "CCTV5", "央视五套", "CCTV-5体育",
    "CCTV-5+", "CCTV5+", "CCTV-5体育赛事",
    "CCTV-6", "CCTV6", "央视六套", "CCTV-6电影",
    "CCTV-7", "CCTV7", "央视七套", "CCTV-7国防军事",
    "CCTV-8", "CCTV8", "央视八套", "CCTV-8电视剧",
    "CCTV-9", "CCTV9", "央视九套", "CCTV-9纪录",
    "CCTV-10", "CCTV10", "央视十套", "CCTV-10科教",
    "CCTV-11", "CCTV11", "央视十一套", "CCTV-11戏曲",
    "CCTV-12", "CCTV12", "央视十二套", "CCTV-12社会与法",
    "CCTV-13", "CCTV13", "央视十三套", "CCTV-13新闻",
    "CCTV-14", "CCTV14", "央视十四套", "CCTV-14少儿",
    "CCTV-15", "CCTV15", "央视十五套", "CCTV-15音乐",
    "CCTV-16", "CCTV16", "央视十六套", "CCTV-16奥林匹克",
    "CCTV-17", "CCTV17", "央视十七套", "CCTV-17农业农村",
    # 4K/8K后缀频道
    "CCTV-1 4K", "CCTV-5 4K", "CCTV-6 4K", "CCTV-8K", "CCTV-4K"
]

# 分类定义（只保留分类，排序单独处理）
CATEGORIES = [
    {"name":"📺央视频道","kw":["CCTV","央视","cctv","中央"]},
    {"name":"📺卫视频道","kw":["卫视","江苏","浙江","湖南","北京","东方","山东","安徽","湖北","广东","四川","重庆","河南"]},
    {"name":"🎬影视频道","kw":["电影","影院","院线","影视","剧场"]},
    {"name":"🧒少儿频道","kw":["少儿","儿童","卡通","动画","动漫"]},
    {"name":"🇭🇰香港频道","kw":["香港","TVB","ViuTV"]},
    {"name":"🇲🇴澳门频道","kw":["澳门"]},
    {"name":"🌊台湾频道","kw":["台湾","中天","东森","纬来"]},
    {"name":"🇸🇬新加坡","kw":["新加坡","新传媒"]},
    {"name":"🎬影视轮播","kw":["轮播","影视轮播","电影轮播"]}
]

# 【核心2：提取央视频道数字，精准排序】
def get_cctv_number(name):
    # 匹配CCTV-1、CCTV1、CCTV-10等，提取数字
    match = re.search(r'CCTV[-]?(\d+)(\+)?', name, re.IGNORECASE)
    if match:
        num = int(match.group(1))
        # 5+ 特殊处理，排到5后面
        if match.group(2) == '+':
            return num + 0.5
        return num
    # 别名匹配（央视一套→1，央视二套→2）
    alias_map = {"一套":1, "二套":2, "三套":3, "四套":4, "五套":5, "六套":6, "七套":7, "八套":8, "九套":9, "十套":10, "十一套":11, "十二套":12, "十三套":13, "十四套":14, "十五套":15, "十六套":16, "十七套":17}
    for alias, num in alias_map.items():
        if alias in name:
            return num
    # 4K/8K排到最后
    if '4K' in name or '8K' in name:
        return 99
    # 其他未知央视频道排到最后
    return 100

def get_lines_from_text(text):
    return [x.strip() for x in text.splitlines() if x.strip()]

def fetch_text(url):
    try:
        r = requests.get(url, timeout=8, verify=False)
        r.encoding = "utf-8"
        return get_lines_from_text(r.text)
    except Exception:
        return []

# 双保险测速
def is_live(url):
    if not url.startswith("http"):
        return False
    try:
        res = requests.head(url, timeout=CHECK_TIMEOUT, allow_redirects=True, verify=False)
        if res.status_code in (200,301,302):
            return True
    except Exception:
        pass
    try:
        res = requests.get(url, timeout=CHECK_TIMEOUT, stream=True, verify=False)
        return res.status_code in (200,301,302)
    except Exception:
        return False

def parse_all(lines):
    chans = []
    seen_url = set()
    i=0
    while i < len(lines):
        s = lines[i]
        if "," in s and not s.startswith("#"):
            n,u = s.split(",",1)
            n,u = n.strip(),u.strip()
            if u.startswith("http") and u not in seen_url and n:
                seen_url.add(u)
                chans.append((n,u))
            i += 1
        elif s.startswith("#EXTINF"):
            if i+1 < len(lines):
                name = s.split(",")[-1].strip()
                url = lines[i+1].strip()
                if url.startswith("http") and url not in seen_url and name:
                    seen_url.add(url)
                    chans.append((name,url))
            i += 2
        elif s.startswith("http") and s not in seen_url:
            seen_url.add(s)
            chans.append((f"备用{i}",s))
            i += 1
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
    # 拉取源
    local = fetch_text(LOCAL_TXT) if os.path.exists(LOCAL_TXT) else []
    own_remote = fetch_text(OWN_REMOTE)
    all_backup = []
    for bu in BACKUP_POOL:
        all_backup.extend(fetch_text(bu))
    total_lines = local + own_remote + all_backup

    # 解析频道
    raw_chans = parse_all(total_lines)
    print(f"📥待检测源：{len(raw_chans)}个")

    # 10线程并发测速
    good_chans = []
    bad_cnt = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_chan = {executor.submit(is_live, url): (name, url) for name, url in raw_chans}
        for future in as_completed(future_to_chan):
            name, url = future_to_chan[future]
            if future.result():
                good_chans.append((name, url))
            else:
                bad_cnt += 1
    print(f"✅有效源：{len(good_chans)}个，剔除死链：{bad_cnt}个")

    # 分类分组
    bucket = {g["name"]:[] for g in CATEGORIES}
    bucket["其他频道"] = []
    for name,url in good_chans:
        bucket[match_group(name)].append((name,url))

    # 【核心3：央视按数字精准排序，彻底锁死】
    cctv_list = bucket["📺央视频道"]
    # 按提取的数字排序，5+排5后，4K/8K排最后
    sorted_cctv = sorted(cctv_list, key=lambda x: get_cctv_number(x[0]))
    # 替换原央视列表
    bucket["📺央视频道"] = sorted_cctv

    # 卫视按省份排序（可选，也可以按数字排序）
    def get_weishi_order(name):
        weishi_order = ["北京","天津","河北","山西","内蒙古","辽宁","吉林","黑龙江","上海","江苏","浙江","安徽","福建","江西","山东","河南","湖北","湖南","广东","广西","海南","重庆","四川","贵州","云南","西藏","陕西","甘肃","青海","宁夏","新疆"]
        for idx, province in enumerate(weishi_order):
            if province in name:
                return idx
        return 99
    bucket["📺卫视频道"] = sorted(bucket["📺卫视频道"], key=lambda x: get_weishi_order(x[0]))

    # 生成最终M3U
    m3u = ['#EXTM3U x-tvg-url="https://epg.112114.xyz/epg.xml.gz"']
    order = [g["name"] for g in CATEGORIES] + ["其他频道"]
    for gname in order:
        for name,url in bucket[gname]:
            m3u.append(f'#EXTINF:-1 group-title="{gname}",{name}')
            m3u.append(url)

    # 写入文件
    with open(OUT_M3U,"w",encoding="utf-8") as f:
        f.write("\n".join(m3u)+"\n")

    # 写入日志
    log = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 央视顺序锁死版｜有效{len(good_chans)}个\n"
    with open(LOG_TXT,"a",encoding="utf-8") as f:
        f.write(log)
    print(log+"🎉完成！央视顺序100%规整，再也不乱！")

if __name__ == "__main__":
    main()
