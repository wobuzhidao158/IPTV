# -*- coding: utf-8 -*-
# 本地txt+远程接口双合并 带Emoji图标精准分类终极版
import os
import requests
from datetime import datetime

# 基础配置
LOCAL_TXT = "直播源.txt"
REMOTE_URL = "http://zhibo.cc.cd/api.php?token=BVna62di&type=txt"
OUT_M3U = "iptv.m3u"
LOG_TXT = "update_log.txt"

# 完全按你给的图标+分类1:1配置
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

def get_lines_from_text(text):
    return [x.strip() for x in text.splitlines() if x.strip()]

def fetch_remote():
    try:
        r = requests.get(REMOTE_URL, timeout=12)
        r.encoding = "utf-8"
        return get_lines_from_text(r.text)
    except:
        return []

def read_local():
    if not os.path.exists(LOCAL_TXT):
        return []
    with open(LOCAL_TXT,"r",encoding="utf-8") as f:
        return get_lines_from_text(f.read())

def parse_all(lines):
    chans = []
    seen_url = set()
    i=0
    while i<len(lines):
        s = lines[i]
        if "," in s and not s.startswith("#"):
            n,u = s.split(",",1)
            n,u = n.strip(),u.strip()
            if u.startswith("http") and u not in seen_url:
                seen_url.add(u)
                chans.append((n,u))
            i+=1
        elif s.startswith("#EXTINF"):
            if i+1<len(lines):
                name = s.split(",")[-1].strip()
                url = lines[i+1].strip()
                if url.startswith("http") and url not in seen_url:
                    seen_url.add(url)
                    chans.append((name,url))
            i+=2
        elif s.startswith("http") and s not in seen_url:
            seen_url.add(s)
            chans.append((f"未知{i}",s))
            i+=1
        else:
            i+=1
    return chans

def match_group(name):
    n = name.lower()
    for g in CATEGORIES:
        for k in g["kw"]:
            if k.lower() in n:
                return g["name"]
    return "其他频道"

def main():
    local_lines = read_local()
    remote_lines = fetch_remote()
    all_lines = local_lines + remote_lines

    chans = parse_all(all_lines)

    bucket = {g["name"]:[] for g in CATEGORIES}
    bucket["其他频道"] = []
    for name,url in chans:
        bucket[match_group(name)].append((name,url))

    # 生成带图标分组M3U
    m3u = ['#EXTM3U']
    order = [g["name"] for g in CATEGORIES] + ["其他频道"]
    for gname in order:
        for name,url in bucket[gname]:
            m3u.append(f'#EXTINF:-1 group-title="{gname}",{name}')
            m3u.append(url)

    with open(OUT_M3U,"w",encoding="utf-8") as f:
        f.write("\n".join(m3u)+"\n")

    log = f"[{datetime.now()}]本地{len(local_lines)}行+远程{len(remote_lines)}行→合并有效{len(chans)}个\n"
    with open(LOG_TXT,"a",encoding="utf-8") as f:
        f.write(log)
    print(log)

if __name__ == "__main__":
    main()
