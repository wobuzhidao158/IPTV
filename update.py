# -*- coding: utf-8 -*-
"""
终极稳定版：全异常捕获 + 低并发 + 快速失败，确保 GitHub Actions 稳定跑完
"""
import os
import re
import time
import requests
import socket
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from collections import defaultdict

# ========== 保守配置（确保任务稳定完成） ==========
LOCAL_TXT = "直播源.txt"
OWN_REMOTE = "https://zhibo.cc.cd/api.php?token=BVna62di&type=txt"
OUT_M3U = "iptv.m3u"
LOG_TXT = "update_log.txt"

TEST_TIMEOUT = 2.0                # 单个源超时 2 秒
MAX_WORKERS = 3                   # 并发数降至 3，避免 GitHub 服务器压力
MIN_SPEED_SCORE = 30
MIN_RESOLUTION_SCORE = 70

BACKUP_POOL = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u"
]

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
        for g in CATEGORIES:
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
        print(f"拉取失败：{url}")
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
        elif "480" in text or "sd" in text:
            return 30
        else:
            return 40
    except:
        return 40

def quick_socket_test(host, port=80, timeout=2):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def test_speed(url):
    """全异常捕获，确保永不抛出异常"""
    try:
        if not url.startswith("http"):
            return (TEST_TIMEOUT, False)
        lower_url = url.lower()
        if any(x in lower_url for x in [".m3u8", ".flv", "rtmp:", ".ts", "live"]):
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                host = parsed.hostname
                if host:
                    port = parsed.port or (443 if parsed.scheme == "https" else 80)
                    if quick_socket_test(host, port, TEST_TIMEOUT):
                        return (0.3, True)
                return (TEST_TIMEOUT, False)
            except:
                return (TEST_TIMEOUT, False)
        start = time.time()
        resp = requests.head(url, timeout=TEST_TIMEOUT, allow_redirects=True, verify=False)
        elapsed = time.time() - start
        if resp.status_code in (200, 301, 302, 304):
            return (elapsed, True)
        else:
            return (TEST_TIMEOUT, False)
    except Exception:
        return (TEST_TIMEOUT, False)

def score_source(resolution_score, response_time):
    if response_time >= TEST_TIMEOUT:
        return 0
    speed_score = max(0, 100 - (response_time / TEST_TIMEOUT * 100))
    total = resolution_score * 0.6 + speed_score * 0.4
    return round(total, 2)

def is_source_qualified(name, url):
    try:
        resp_time, ok = test_speed(url)
        if not ok or resp_time >= TEST_TIMEOUT:
            return False, 0, resp_time
        res_score = extract_resolution(name, url)
        if res_score < MIN_RESOLUTION_SCORE:
            return False, res_score, resp_time
        speed_score = max(0, 100 - (resp_time / TEST_TIMEOUT * 100))
        if speed_score < MIN_SPEED_SCORE:
            return False, res_score, resp_time
        total = score_source(res_score, resp_time)
        return True, total, resp_time
    except:
        return False, 0, TEST_TIMEOUT

def select_best(candidates):
    valid = []
    for name, url, src_type in candidates:
        try:
            qualified, total, resp_time = is_source_qualified(name, url)
            if qualified:
                valid.append((total, resp_time, name, url, src_type))
        except:
            continue
    if not valid:
        return None
    valid.sort(key=lambda x: (-x[0], x[1]))
    return (valid[0][2], valid[0][3])

def normalize_name(name):
    try:
        return re.sub(r"\s*[\[\(]?(\d+[Pp]|4K|8K|HD|FHD|UHD|超清|高清|标清)[\]\)]?\s*", "", name, flags=re.IGNORECASE).strip()
    except:
        return name.strip()

def main():
    requests.packages.urllib3.disable_warnings()
    start_time = time.time()

    print("🚀 开始执行直播源更新任务...")

    # 1. 本地源
    local_sources = []
    if os.path.exists(LOCAL_TXT):
        try:
            with open(LOCAL_TXT, "r", encoding="utf-8") as f:
                lines = cut_lines(f.read())
            local_sources = parse_sources(lines, source_type="local")
            print(f"✅ 本地私源读取：{len(local_sources)} 个链接")
        except Exception as e:
            print(f"⚠️ 读取本地源失败：{e}")
    else:
        print("⚠️ 未找到本地直播源.txt")

    # 2. API 私源
    api_sources = []
    try:
        api_sources = parse_sources(fetch_src(OWN_REMOTE), source_type="network")
        print(f"✅ API私源读取：{len(api_sources)} 个链接")
    except:
        print("⚠️ API私源拉取失败，继续执行")

    # 3. 公共源
    backup_lines = []
    for src in BACKUP_POOL:
        try:
            backup_lines.extend(fetch_src(src))
        except:
            pass
    public_sources = parse_sources(backup_lines, source_type="network")
    print(f"🌐 公共备用源链接数：{len(public_sources)}")

    # 4. 合并分组
    groups = defaultdict(list)
    seen_urls = set()

    for name, url, stype in local_sources:
        if url in seen_urls:
            continue
        seen_urls.add(url)
        base = normalize_name(name)
        groups[base].append((name, url, stype))

    for name, url, stype in api_sources + public_sources:
        if url in seen_urls:
            continue
        base = normalize_name(name)
        groups[base].append((name, url, stype))
        seen_urls.add(url)

    total_channels = len(groups)
    print(f"📋 合并后总频道数：{total_channels} 个")

    # 5. 逐频道择优（使用线程池但捕获整体超时）
    print("\n⚡ 开始频道筛选（本地源优先）...")
    best_per_channel = []
    local_kept = 0
    network_used = 0
    discarded = 0

    processed = 0
    for base, candidates in groups.items():
        processed += 1
        if processed % 50 == 0:
            print(f"  进度：{processed}/{total_channels}")

        try:
            local_cands = [c for c in candidates if c[2] == "local"]
            network_cands = [c for c in candidates if c[2] == "network"]

            best = None
            if local_cands:
                best = select_best(local_cands)
                if best:
                    local_kept += 1
                else:
                    best = select_best(network_cands)
                    if best:
                        network_used += 1
                    else:
                        discarded += 1
            else:
                best = select_best(network_cands)
                if best:
                    network_used += 1
                else:
                    discarded += 1

            if best:
                best_per_channel.append(best)
        except Exception as e:
            print(f"  ⚠️ 处理频道 {base} 时出错：{e}，跳过")
            discarded += 1
            continue

    print(f"\n✅ 筛选完成：保留 {len(best_per_channel)} 个频道")
    print(f"   - 保留本地源：{local_kept} 个")
    print(f"   - 使用网络源：{network_used} 个")
    print(f"   - 丢弃无可用源：{discarded} 个")

    # 6. 分组排序
    bucket = {g["name"]: [] for g in CATEGORIES}
    bucket["其他频道"] = []
    for name, url in best_per_channel:
        bucket[match_group(name)].append((name, url))

    try:
        bucket["📺央视频道"].sort(key=lambda x: get_cctv_sort_key(x[0]))
        bucket["📺卫视频道"].sort(key=lambda x: get_websort(x[0]))
    except:
        pass

    # 7. 写入 M3U
    if os.path.exists(OUT_M3U):
        os.remove(OUT_M3U)

    with open(OUT_M3U, "w", encoding="utf-8") as f:
        f.write('#EXTM3U x-tvg-url="https://epg.112114.xyz/epg.xml.gz"\n')
        order = [g["name"] for g in CATEGORIES] + ["其他频道"]
        for gname in order:
            for name, url in bucket[gname]:
                f.write(f'#EXTINF:-1 group-title="{gname}",{name}\n')
                f.write(url + "\n")

    # 8. 日志
    elapsed = time.time() - start_time
    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 本地保留{local_kept} | 网络补充{network_used} | 丢弃{discarded} | 总{len(best_per_channel)} | 耗时{elapsed:.1f}s\n"
    with open(LOG_TXT, "a", encoding="utf-8") as f:
        f.write(log_msg)
    print("\n" + log_msg)
    print("🎉 执行完毕！")

if __name__ == "__main__":
    main()