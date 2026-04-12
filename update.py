# -*- coding: utf-8 -*-
import os
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

LOCAL_TXT = "直播源.txt"
OWN_REMOTE = "https://zhibo.cc.cd/api.php?token=BVna62di&type=txt"
OUT_M3U = "iptv.m3u"
LOG_TXT = "update_log.txt"
CHECK_TIMEOUT = 8
BACKUP_POOL = ["https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u"]

CATEGORIES = [
    {"name":"📺央视频道","kw":["CCTV","央视","cctv","中央"]},
    {"name":"📺卫视频道","kw":["卫视"]},
    {"name":"🎬影视频道","kw":["电影","影院","院线","影视","剧场"]},
    {"name":"🧒少儿频道","kw":["少儿","儿童","卡通","动画","动漫"]},
    {"name":"🇭🇰香港频道","kw":["香港","TVB","ViuTV"]},
    {"name":"🇲🇴澳门频道","kw":["澳门"]},
    {"name":"🌏台湾频道","kw":["台湾","中天","东森","纬来"]},
    {"name":"🇸🇬新加坡频道","kw":["新加坡","新传媒"]},
    {"name":"🎬影视轮播","kw":["轮播","影视轮播","电影轮播"]}
]
PROVINCE_ORDER = ["北京","天津","河北","山西","内蒙古","辽宁","吉林","黑龙江",
                  "上海","江苏","浙江","安徽","福建","江西","山东","河南","湖北",
                  "湖南","广东","广西","海南","重庆","四川","贵州","云南","陕西",
                  "甘肃","宁夏","新疆"]

def get_cctv_sort_key(name):
    m = re.search(r'CCTV[-]?(\d+)(\+)?', name, re.IGNORECASE)
    if m:
        num = int(m.group(1))
        return num + 0.5 if m.group(2) == '+' else num
    alias = {"一套":1,"二套":2,"三套":3,"四套":4,"五套":5,"六套":6,"七套":7,"八套":8,
             "九套":9,"十套":10,"十一套":11,"十二套":12,"十三套":13,"十四套":14,
             "十五套":15,"十六套":16,"十七套":17}
    for a,n in alias.items():
        if a in name:
            return n
    return 99

def get_websort(name):
    for idx,p in enumerate(PROVINCE_ORDER):
        if p in name:
            return idx
    return 999

def match_group(name):
    low = name.lower()
    for g in CATEGORIES:
        for k in g["kw"]:
            if k.lower() in low:
                return g["name"]
    return "其他频道"

def cut_lines(text):
    return [x.strip() for x in text.splitlines() if x.strip()]

def fetch_src(url):
    try:
        r = requests.get(url, timeout=15, verify=False)
        r.encoding = "utf-8"
        return cut_lines(r.text)
    except:
        return []

def safe_check(url):
    if not url.startswith("http"): return False
    if any(x in url.lower() for x in ["m3u8","ts","live"]): return True
    try:
        res = requests.head(url, timeout=CHECK_TIMEOUT, allow_redirects=True, verify=False)
        return res.status_code in (200,301,302,304)
    except:
        return False

def parse_mix(lines):
    """增强解析：自动忽略 #genre# 等注释，支持 频道名,URL 和 M3U 格式"""
    arr, seen = [], set()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#genre#"):  # 跳过空行和注释
            i += 1
            continue
        
        # 格式1: 频道名,URL (且URL以http开头)
        if "," in line and not line.startswith("#"):
            parts = line.split(",", 1)
            if len(parts) == 2:
                n, u = parts[0].strip(), parts[1].strip()
                if u.startswith("http") and u not in seen and n:
                    seen.add(u)
                    arr.append((n, u))
            i += 1
        # 格式2: M3U标准
        elif line.startswith("#EXTINF"):
            n = line.split(",")[-1].strip()
            if i+1 < len(lines):
                u = lines[i+1].strip()
                if u.startswith("http") and u not in seen and n:
                    seen.add(u)
                    arr.append((n, u))
                i += 2
            else:
                i += 1
        else:
            i += 1
    return arr

def main():
    requests.packages.urllib3.disable_warnings()

    # 1. 绝对优先读本地
    local_private = []
    if os.path.exists(LOCAL_TXT):
        with open(LOCAL_TXT, "r", encoding="utf-8") as f:
            lines = cut_lines(f.read())
        local_private = parse_mix(lines)
        print(f"✅ 本地私源读取：{len(local_private)} 个频道")
    else:
        print("⚠️ 本地文件不存在")

    # 2. 读取 API 私源
    api_private = parse_mix(fetch_src(OWN_REMOTE))
    print(f"✅ API私源读取：{len(api_private)} 个")

    # 3. 合并并建立保护
    protected_names = set()
    protected_urls = set()
    final = []
    for n,u in local_private + api_private:
        if u in protected_urls or n.lower() in protected_names:
            continue
        protected_names.add(n.lower())
        protected_urls.add(u)
        final.append((n,u))
    print(f"🔒 私源合并后受保护：{len(final)} 个")

    # 4. 公共源补充
    backup_all = []
    for b in BACKUP_POOL:
        backup_all.extend(fetch_src(b))
    new_candidates = parse_mix(backup_all)
    new_only = [(n,u) for n,u in new_candidates if u not in protected_urls and n.lower() not in protected_names]
    print(f"🆕 候选新源：{len(new_only)} 个")

    # 5. 新源存活校验
    alive_new = []
    if new_only:
        with ThreadPoolExecutor(max_workers=10) as ex:
            tasks = {ex.submit(safe_check, u): (n,u) for n,u in new_only}
            for f in as_completed(tasks):
                n,u = tasks[f]
                if f.result():
                    alive_new.append((n,u))
        print(f"✅ 新源存活：{len(alive_new)} 个")

    # 6. 合并最终列表
    for n,u in alive_new:
        if u not in protected_urls and n.lower() not in protected_names:
            final.append((n,u))
    print(f"📋 最终频道总数：{len(final)}")

    # 7. 分组排序
    bucket = {g["name"]: [] for g in CATEGORIES}
    bucket["其他频道"] = []
    for n,u in final:
        bucket[match_group(n)].append((n,u))
    bucket["📺央视频道"].sort(key=lambda x: get_cctv_sort_key(x[0]))
    bucket["📺卫视频道"].sort(key=lambda x: get_websort(x[0]))

    # 8. 写入文件
    if os.path.exists(OUT_M3U):
        os.remove(OUT_M3U)
    m3u = ['#EXTM3U x-tvg-url="https://epg.112114.xyz/epg.xml.gz"']
    order = [g["name"] for g in CATEGORIES] + ["其他频道"]
    for gname in order:
        for n,u in bucket[gname]:
            m3u.append(f'#EXTINF:-1 group-title="{gname}",{n}')
            m3u.append(u)
    with open(OUT_M3U,"w",encoding="utf-8") as f:
        f.write("\n".join(m3u)+"\n")

    log_msg = f"[{datetime.now()}] 私源{len(local_private)+len(api_private)} | 新增{len(alive_new)} | 总{len(final)}\n"
    with open(LOG_TXT,"a",encoding="utf-8") as f:
        f.write(log_msg)
    print(log_msg + "🎉 完成！本地源绝对优先。")

if __name__ == "__main__":
    main()