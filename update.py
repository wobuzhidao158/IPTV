# -*- coding: utf-8 -*-
# 全频道规整+多线程极速版｜央视+卫视+少儿+影视全排序，10线程并发，3-5分钟跑完
import os
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ========== 基础配置勿改 ==========
LOCAL_TXT = "直播源.txt"
OWN_REMOTE = "https://zhibo.cc.cd/api.php?token=BVna62di&type=txt"
OUT_M3U = "iptv.m3u"
LOG_TXT = "update_log.txt"
CHECK_TIMEOUT = 2.5
BACKUP_POOL = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u"
]
# =================================

# 分类定义
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

# 1.央视固定排序表
CCTV_ORDER = [
    "CCTV-1","CCTV-2","CCTV-3","CCTV-4","CCTV-5","CCTV-5+",
    "CCTV-6","CCTV-7","CCTV-8","CCTV-9","CCTV-10","CCTV-11",
    "CCTV-12","CCTV-13","CCTV-14","CCTV-15","CCTV-16","CCTV-17",
    "CCTV-4K","CCTV-8K"
]

# 2.卫视固定省份排序表
WEISHI_ORDER = [
    "北京卫视","天津卫视","河北卫视","山西卫视","内蒙古卫视",
    "辽宁卫视","吉林卫视","黑龙江卫视","上海东方卫视","江苏卫视",
    "浙江卫视","安徽卫视","福建卫视","江西卫视","山东卫视",
    "河南卫视","湖北卫视","湖南卫视","广东卫视","广西卫视",
    "海南卫视","重庆卫视","四川卫视","贵州卫视","云南卫视",
    "西藏卫视","陕西卫视","甘肃卫视","青海卫视","宁夏卫视","新疆卫视"
]

def get_lines_from_text(text):
    return [x.strip() for x in text.splitlines() if x.strip()]

def fetch_text(url):
    try:
        r = requests.get(url, timeout=8, verify=False)
        r.encoding = "utf-8"
        return get_lines_from_text(r.text)
    except Exception:
        return []

# 双保险存活检测（多线程用）
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

# 通用分组排序函数
def sort_by_keyword_list(src_list, order_list):
    sorted_ok = []
    for kw in order_list:
        for name,url in src_list:
            if kw in name and (name,url) not in sorted_ok:
                sorted_ok.append((name,url))
    for item in src_list:
        if item not in sorted_ok:
            sorted_ok.append(item)
    return sorted_ok

def main():
    requests.packages.urllib3.disable_warnings()
    local = fetch_text(LOCAL_TXT) if os.path.exists(LOCAL_TXT) else []
    own_remote = fetch_text(OWN_REMOTE)
    all_backup = []
    for bu in BACKUP_POOL:
        all_backup.extend(fetch_text(bu))
    total_lines = local + own_remote + all_backup

    raw_chans = parse_all(total_lines)
    print(f"📥待检测源数量：{len(raw_chans)}个")

    # 【核心提速】10线程并发测速，耗时直接砍半
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

    # 归类+强制排序
    bucket = {g["name"]:[] for g in CATEGORIES}
    bucket["其他频道"] = []
    for name,url in good_chans:
        bucket[match_group(name)].append((name,url))

    bucket["📺央视频道"] = sort_by_keyword_list(bucket["📺央视频道"], CCTV_ORDER)
    bucket["📺卫视频道"] = sort_by_keyword_list(bucket["📺卫视频道"], WEISHI_ORDER)

    # 生成最终M3U
    m3u = ['#EXTM3U x-tvg-url="https://epg.112114.xyz/epg.xml.gz"']
    order = [g["name"] for g in CATEGORIES] + ["其他频道"]
    for gname in order:
        for name,url in bucket[gname]:
            m3u.append(f'#EXTINF:-1 group-title="{gname}",{name}')
            m3u.append(url)

    with open(OUT_M3U,"w",encoding="utf-8") as f:
        f.write("\n".join(m3u)+"\n")

    log = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 多线程极速全频道规整版｜有效{len(good_chans)}个\n"
    with open(LOG_TXT,"a",encoding="utf-8") as f:
        f.write(log)
    print(log+"🎉全部完成！3-5分钟跑完，再也不超时！")

if __name__ == "__main__":
    main()
