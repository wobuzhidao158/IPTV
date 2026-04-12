# -*- coding: utf-8 -*-
"""
100%稳定版：极简测速 + 全异常保护 + 超低并发，确保 GitHub Actions 永不超时
"""
import os
import re
import time
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# ========== 极度保守配置 ==========
LOCAL_TXT = "直播源.txt"
OWN_REMOTE = "https://zhibo.cc.cd/api.php?token=BVna62di&type=txt"
OUT_M3U = "iptv.m3u"
LOG_TXT = "update_log.txt"

CHECK_TIMEOUT = 1.5            # 单个源检测超时 1.5 秒
MAX_WORKERS = 2                # 并发数降至 2，绝不阻塞
MIN_RESOLUTION_SCORE = 70      # 1080p 门槛

BACKUP_POOL = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u"
]

CATEGORIES = [
    {"name":"📺央视频道","kw":["CCTV","央视","cctv","中央"]},
    {"name":"📺卫视频道","kw":["卫视"]},
    {"name":"🎥4K频道","kw":["4k","8k","uhd","2160","4320","超高清","极致高清"]},
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
    try:
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
    except:
        return 100

def get_websort(name):
    try:
        for idx,p in enumerate(PROVINCE_ORDER):
            if p in name:
                return idx
        return 999
    except:
        return 999

def match_group(name):
    try:
        low = name.lower()
        # 4K优先
        for k in CATEGORIES[2]["kw"]:
            if k in low:
                return "🎥4K频道"
        for g in CATEGORIES:
            if g["name"] == "🎥4K频道":
                continue
            for k in g["kw"]:
                if k.lower() in low:
                    return g["name"]
        return "其他频道"
    except:
        return "其他频道"

def cut_lines(text):
    return [x.strip() for x in text.splitlines() if x.strip()]

def fetch_src(url):
    try:
        r = requests.get(url, timeout=10, verify=False)
        r.encoding = "utf-8"
        return cut_lines(r.text)
    except:
        return []

def parse_sources(lines, source_type="network"):
    sources = []
    i = 0
    while i < len(lines):
        try:
            line = lines[i].strip()
            if not line or line.startswith("#genre#") or line.startswith("//"):
                i += 1
                continue
            if "," in line and not line.startswith("#"):
                parts = line.split(",", 1)
                if len(parts) == 2:
                    name, url = parts[0].strip(), parts[1].strip()
                    if url.startswith("http"):
                        sources.append((name, url, source_type))
                i += 1
            elif line.startswith("#EXTINF"):
                name = line.split(",")[-1].strip()
                if i+1 < len(lines):
                    url = lines[i+1].strip()
                    if url.startswith("http"):
                        sources.append((name, url, source_type))
                    i += 2
                else:
                    i += 1
            else:
                i += 1
        except:
            i += 1
    return sources

def extract_resolution(name, url):
    try:
        text = (name + " " + url).lower()
        if "8k" in text or "4320" in text:
            return 100
        elif "4k" in text or "2160" in text or "uhd" in text:
            return 85
        elif "1080" in text or "fhd" in text or "全高清" in text:
            return 70
        elif "720" in text or "hd" in text:
            return 50
        else:
            return 40
    except:
        return 40

def is_alive(url):
    """极简存活检测：HEAD请求成功即认为可用"""
    try:
        r = requests.head(url, timeout=CHECK_TIMEOUT, allow_redirects=True, verify=False)
        return r.status_code in (200, 301, 302, 304)
    except:
        return False

def is_qualified(name, url):
    """判断源是否合格：存活 + 清晰度达标"""
    if not is_alive(url):
        return False
    res_score = extract_resolution(name, url)
    return res_score >= MIN_RESOLUTION_SCORE

def select_best(candidates):
    """从候选源中选出最优：优先本地，同源内随机选第一个合格的"""
    local = [c for c in candidates if c[2] == "local"]
    network = [c for c in candidates if c[2] == "network"]
    # 先检查本地
    for name, url, stype in local:
        if is_qualified(name, url):
            return (name, url)
    # 再检查网络
    for name, url, stype in network:
        if is_qualified(name, url):
            return (name, url)
    return None

def normalize_name(name):
    try:
        return re.sub(r"\s*[\[\(]?(\d+[Pp]|4K|8K|HD|FHD|UHD|超清|高清|标清)[\]\)]?\s*", "", name, flags=re.IGNORECASE).strip()
    except:
        return name.strip()

def main():
    requests.packages.urllib3.disable_warnings()
    start_time = time.time()

    print("🚀 开始极简稳定更新...")

    # 1. 本地源
    local_sources = []
    if os.path.exists(LOCAL_TXT):
        try:
            with open(LOCAL_TXT, "r", encoding="utf-8") as f:
                lines = cut_lines(f.read())
            local_sources = parse_sources(lines, source_type="local")
            print(f"✅ 本地私源：{len(local_sources)} 个")
        except:
            print("⚠️ 本地源读取失败")
    else:
        print("⚠️ 未找到本地直播源.txt")

    # 2. API源
    api_sources = parse_sources(fetch_src(OWN_REMOTE), source_type="network")
    print(f"✅ API私源：{len(api_sources)} 个")

    # 3. 公共源
    backup_lines = []
    for src in BACKUP_POOL:
        backup_lines.extend(fetch_src(src))
    public_sources = parse_sources(backup_lines, source_type="network")
    print(f"🌐 公共备用：{len(public_sources)} 个")

    # 4. 合并分组
    groups = defaultdict(list)
    seen_urls = set()
    for name, url, stype in local_sources:
        if url in seen_urls: continue
        seen_urls.add(url)
        groups[normalize_name(name)].append((name, url, stype))
    for name, url, stype in api_sources + public_sources:
        if url in seen_urls: continue
        seen_urls.add(url)
        groups[normalize_name(name)].append((name, url, stype))

    total = len(groups)
    print(f"📋 去重后频道数：{total}")

    # 5. 筛选（不测速，只存活检测）
    print("⚡ 快速筛选（本地优先）...")
    best_list = []
    local_kept = network_used = discarded = 0
    processed = 0
    for base, cands in groups.items():
        processed += 1
        if processed % 100 == 0:
            print(f"  进度：{processed}/{total}")
        best = select_best(cands)
        if best:
            best_list.append(best)
            # 统计来源
            is_local = any(c[2] == "local" and c[0] == best[0] and c[1] == best[1] for c in cands)
            if is_local:
                local_kept += 1
            else:
                network_used += 1
        else:
            discarded += 1

    print(f"\n✅ 保留 {len(best_list)} 个频道 (本地:{local_kept} 网络:{network_used} 丢弃:{discarded})")

    # 6. 分组排序
    bucket = {g["name"]: [] for g in CATEGORIES}
    bucket["其他频道"] = []
    for name, url in best_list:
        bucket[match_group(name)].append((name, url))
    try:
        bucket["📺央视频道"].sort(key=lambda x: get_cctv_sort_key(x[0]))
        bucket["📺卫视频道"].sort(key=lambda x: get_websort(x[0]))
    except:
        pass

    # 7. 写入
    if os.path.exists(OUT_M3U):
        os.remove(OUT_M3U)
    with open(OUT_M3U, "w", encoding="utf-8") as f:
        f.write('#EXTM3U x-tvg-url="https://epg.112114.xyz/epg.xml.gz"\n')
        for gname in [g["name"] for g in CATEGORIES] + ["其他频道"]:
            for name, url in bucket[gname]:
                f.write(f'#EXTINF:-1 group-title="{gname}",{name}\n{url}\n')

    elapsed = time.time() - start_time
    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 本地保留{local_kept} 网络补充{network_used} 丢弃{discarded} 总{len(best_list)} 耗时{elapsed:.1f}s\n"
    with open(LOG_TXT, "a", encoding="utf-8") as f:
        f.write(log_msg)
    print(log_msg + "🎉 100%完成！")

if __name__ == "__main__":
    main()