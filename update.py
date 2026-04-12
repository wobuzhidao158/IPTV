# -*- coding: utf-8 -*-
# 方案B 央视顺序规整版：本地+远程双合+测速删失效+全网补新+带图标分类
import os
import requests
from datetime import datetime

# ========== 基础配置勿改 ==========
LOCAL_TXT = "直播源.txt"
OWN_REMOTE = "https://zhibo.cc.cd/api.php?token=BVna62di&type=txt"
OUT_M3U = "iptv.m3u"
LOG_TXT = "update_log.txt"
CHECK_TIMEOUT = 2.5   # 缩短超时，极速测速
# 全网备用源池
BACKUP_POOL = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u"
]
# =================================

# 带Emoji图标分类
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

# 央视频道强制排序规则（严格按1→2→3…排列，可自行增删）
CCTV_ORDER = [
    "CCTV-1", "CCTV-2", "CCTV-3", "CCTV-4", "CCTV-5", "CCTV-5+",
    "CCTV-6", "CCTV-7", "CCTV-8", "CCTV-9", "CCTV-10", "CCTV-11",
    "CCTV-12", "CCTV-13", "CCTV-14", "CCTV-15", "CCTV-16", "CCTV-17",
    "CCTV-4K", "CCTV-8K"
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

# 极速存活检测：仅HEAD，2.5s超时，1分钟内跑完
def is_live(url):
    if not url.startswith("http"):
        return False
    try:
        res = requests.head(url, timeout=CHECK_TIMEOUT, allow_redirects=True, verify=False)
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
    # 关闭requests警告
    requests.packages.urllib3.disable_warnings()
    
    # 1. 三路源合并
    local = fetch_text(LOCAL_TXT) if os.path.exists(LOCAL_TXT) else []
    own_remote = fetch_text(OWN_REMOTE)
    all_backup = []
    for bu in BACKUP_POOL:
        all_backup.extend(fetch_text(bu))
    total_lines = local + own_remote + all_backup
    print(f"📥汇总源行数：{len(total_lines)}")

    # 2. 解析频道
    raw_chans = parse_all(total_lines)
    print(f"🔍待检测：{len(raw_chans)}个")

    # 3. 极速测速
    good_chans = []
    bad_cnt = 0
    for name,url in raw_chans:
        if is_live(url):
            good_chans.append((name,url))
        else:
            bad_cnt += 1
    print(f"✅有效：{len(good_chans)}个，剔除：{bad_cnt}个")

    # 4. 按分类分组 + 央视强制排序
    bucket = {g["name"]:[] for g in CATEGORIES}
    bucket["其他频道"] = []
    for name,url in good_chans:
        bucket[match_group(name)].append((name,url))

    # 给央视频道按指定顺序重新排列
    cctv_list = bucket["📺央视频道"]
    sorted_cctv = []
    # 先匹配顺序内的频道
    for cctv_name in CCTV_ORDER:
        for name, url in cctv_list:
            if name.startswith(cctv_name) and (name, url) not in sorted_cctv:
                sorted_cctv.append((name, url))
    # 再补全剩下的央视频道
    for name, url in cctv_list:
        if (name, url) not in sorted_cctv:
            sorted_cctv.append((name, url))
    # 替换原央视列表
    bucket["📺央视频道"] = sorted_cctv

    # 5. 生成带分类的M3U
    m3u = ['#EXTM3U x-tvg-url="https://epg.112114.xyz/epg.xml.gz"']
    order = [g["name"] for g in CATEGORIES] + ["其他频道"]
    for gname in order:
        for name,url in bucket[gname]:
            m3u.append(f'#EXTINF:-1 group-title="{gname}",{name}')
            m3u.append(url)

    # 6. 写入最终M3U
    with open(OUT_M3U,"w",encoding="utf-8") as f:
        f.write("\n".join(m3u)+"\n")

    # 7. 写入更新日志
    log = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 央视顺序规整版｜有效{len(good_chans)}个\n"
    with open(LOG_TXT,"a",encoding="utf-8") as f:
        f.write(log)
    print(log+"🎉完成！央视顺序已规整！")

if __name__ == "__main__":
    main()
