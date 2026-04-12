# -*- coding: utf-8 -*-
"""
私源绝对优先｜响应时间≤3秒｜失效自动清除｜每频道只留最优一条
- 本地直播源.txt 全部保留并测速择优
- API私源作为补充，同样测速择优
- 网络公共源仅补充新频道，同样测速择优
- 最终每个频道只有一条最稳定/清晰/流畅的源
"""
import os
import re
import time
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# ========== 配置参数 ==========
LOCAL_TXT = "直播源.txt"          # 你的本地私源（绝对优先）
OWN_REMOTE = "https://zhibo.cc.cd/api.php?token=BVna62di&type=txt"  # 你的API私源
OUT_M3U = "iptv.m3u"
LOG_TXT = "update_log.txt"

TEST_TIMEOUT = 3                  # 单个源超时时间（秒）—— 切换频道不超过3秒
MAX_WORKERS = 20                  # 并发测速线程数
MIN_SPEED_SCORE = 30              # 最低速度得分（0-100），低于此值视为不稳定丢弃

BACKUP_POOL = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u"
]

# 分类标签（仅用于分组显示，不影响择优逻辑）
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

# ========== 工具函数 ==========
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
        print(f"拉取失败：{url}")
        return []

def parse_sources(lines):
    """
    解析直播源行，返回 [(频道名, URL), ...]
    支持：频道名,URL  或  #EXTINF 格式
    """
    sources = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#genre#") or line.startswith("//"):
            i += 1
            continue

        if "," in line and not line.startswith("#"):
            parts = line.split(",", 1)
            if len(parts) == 2:
                name, url = parts[0].strip(), parts[1].strip()
                if url.startswith("http"):
                    sources.append((name, url))
            i += 1
        elif line.startswith("#EXTINF"):
            name = line.split(",")[-1].strip()
            if i+1 < len(lines):
                url = lines[i+1].strip()
                if url.startswith("http"):
                    sources.append((name, url))
                i += 2
            else:
                i += 1
        else:
            i += 1
    return sources

def extract_resolution(name, url):
    """从名称或URL中评估清晰度得分（越高越清晰）"""
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

def test_speed(url):
    """
    测速：返回 (响应时间秒, 是否可用)
    超过 TEST_TIMEOUT 秒直接判定失败
    """
    try:
        start = time.time()
        resp = requests.head(url, timeout=TEST_TIMEOUT, allow_redirects=True, verify=False)
        elapsed = time.time() - start
        if resp.status_code in (200, 301, 302, 304):
            return (elapsed, True)
        else:
            return (TEST_TIMEOUT, False)
    except:
        return (TEST_TIMEOUT, False)

def score_source(resolution_score, response_time):
    """
    综合评分：
    - 清晰度权重 0.6
    - 速度权重 0.4（响应时间越短得分越高，超过3秒直接0分）
    """
    if response_time >= TEST_TIMEOUT:
        return 0
    # 速度得分：响应时间 0.5 秒内满分，3秒线性衰减至0
    speed_score = max(0, 100 - (response_time / TEST_TIMEOUT * 100))
    total = resolution_score * 0.6 + speed_score * 0.4
    return round(total, 2)

def select_best_from_candidates(candidates):
    """
    从一组候选源中选出最优的一个
    要求：必须响应时间 ≤3秒，且速度得分 ≥ MIN_SPEED_SCORE
    """
    valid_candidates = []
    print(f"  ⏳ 频道「{candidates[0][0]}」共{len(candidates)}个源，测速中...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        future_to_cand = {ex.submit(test_speed, url): (name, url) for name, url in candidates}
        for f in as_completed(future_to_cand):
            name, url = future_to_cand[f]
            resp_time, ok = f.result()
            if not ok or resp_time >= TEST_TIMEOUT:
                print(f"     ❌ {name} 超时/失效 (>{TEST_TIMEOUT}s)")
                continue
            res_score = extract_resolution(name, url)
            total = score_source(res_score, resp_time)
            speed_score = max(0, 100 - (resp_time / TEST_TIMEOUT * 100))
            print(f"     {name} | 清晰:{res_score} | 响应:{resp_time:.2f}s | 速度分:{speed_score:.1f} | 总分:{total}")
            if speed_score >= MIN_SPEED_SCORE:
                valid_candidates.append((total, resp_time, name, url))
            else:
                print(f"     ⚠️ 速度分过低({speed_score:.1f}<{MIN_SPEED_SCORE})，丢弃")

    if not valid_candidates:
        print(f"  🚫 无可用稳定源，该频道被丢弃")
        return None

    # 按总分降序，同分则选响应时间更短的
    valid_candidates.sort(key=lambda x: (-x[0], x[1]))
    best = valid_candidates[0]
    print(f"  ✅ 选用：{best[2]} (总分 {best[0]}, 响应 {best[1]:.2f}s)")
    return (best[2], best[3])

def normalize_name(name):
    """去除分辨率等后缀，用于频道分组"""
    return re.sub(r"\s*[\[\(]?(\d+[Pp]|4K|8K|HD|FHD|UHD|超清|高清|标清)[\]\)]?\s*", "", name, flags=re.IGNORECASE).strip()

# ========== 主流程 ==========
def main():
    requests.packages.urllib3.disable_warnings()
    start_time = time.time()

    # 1. 读取本地私源（绝对优先）
    local_sources = []
    if os.path.exists(LOCAL_TXT):
        with open(LOCAL_TXT, "r", encoding="utf-8") as f:
            lines = cut_lines(f.read())
        local_sources = parse_sources(lines)
        print(f"✅ 本地私源读取：{len(local_sources)} 个链接")
    else:
        print("⚠️ 未找到本地直播源.txt")

    # 2. 读取API私源
    api_sources = parse_sources(fetch_src(OWN_REMOTE))
    print(f"✅ API私源读取：{len(api_sources)} 个链接")

    # 3. 合并私源（本地+API），按归一化频道名分组
    groups = defaultdict(list)
    seen_urls = set()
    for name, url in local_sources + api_sources:
        if url in seen_urls:
            continue
        seen_urls.add(url)
        base = normalize_name(name)
        groups[base].append((name, url))

    print(f"🔒 私源合并后频道数：{len(groups)} 个（含多源）")

    # 4. 网络公共源补充（只补充私源完全没有的频道）
    backup_lines = []
    for src in BACKUP_POOL:
        backup_lines.extend(fetch_src(src))
    public_sources = parse_sources(backup_lines)
    print(f"🌐 公共备用源链接数：{len(public_sources)}")

    for name, url in public_sources:
        if url in seen_urls:
            continue
        base = normalize_name(name)
        if base not in groups:
            groups[base].append((name, url))
            seen_urls.add(url)

    print(f"📋 合并后总频道数（去重前）：{len(groups)}")

    # 5. 每个频道内部择优，只留一个最佳源（必须稳定且响应≤3秒）
    print("\n⚡ 开始频道内择优（仅保留响应≤3秒且速度分≥{}的源）...".format(MIN_SPEED_SCORE))
    best_per_channel = []
    discarded = 0
    for base, candidates in groups.items():
        best = select_best_from_candidates(candidates)
        if best:
            best_per_channel.append(best)
        else:
            discarded += 1

    print(f"\n✅ 择优完成：保留 {len(best_per_channel)} 个频道，丢弃 {discarded} 个无稳定源的频道")

    # 6. 分组排序（仅用于M3U输出顺序）
    bucket = {g["name"]: [] for g in CATEGORIES}
    bucket["其他频道"] = []
    for name, url in best_per_channel:
        bucket[match_group(name)].append((name, url))

    bucket["📺央视频道"].sort(key=lambda x: get_cctv_sort_key(x[0]))
    bucket["📺卫视频道"].sort(key=lambda x: get_websort(x[0]))

    # 7. 写入M3U文件（彻底覆盖）
    if os.path.exists(OUT_M3U):
        os.remove(OUT_M3U)

    with open(OUT_M3U, "w", encoding="utf-8") as f:
        f.write('#EXTM3U x-tvg-url="https://epg.112114.xyz/epg.xml.gz"\n')
        order = [g["name"] for g in CATEGORIES] + ["其他频道"]
        for gname in order:
            for name, url in bucket[gname]:
                f.write(f'#EXTINF:-1 group-title="{gname}",{name}\n')
                f.write(url + "\n")

    # 8. 日志记录
    elapsed = time.time() - start_time
    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 本地{len(local_sources)}链接 | 最终{len(best_per_channel)}频道 | 丢弃{discarded} | 耗时{elapsed:.1f}s\n"
    with open(LOG_TXT, "a", encoding="utf-8") as f:
        f.write(log_msg)
    print("\n" + log_msg)
    print("🎉 执行完毕！每个频道仅保留一条最稳定/清晰/流畅的源（响应≤3秒）。")

if __name__ == "__main__":
    main()