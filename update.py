# -*- coding: utf-8 -*-
# 私源优先 + 只保留1080p及以上高清频道
import os
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# ========== 基础配置 ==========
LOCAL_TXT = "直播源.txt"          # 你的本地私源
OWN_REMOTE = "https://zhibo.cc.cd/api.php?token=BVna62di&type=txt"  # 你的API私源
OUT_M3U = "iptv.m3u"
LOG_TXT = "update_log.txt"
CHECK_TIMEOUT = 8
BACKUP_POOL = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u"
]

# ========== 分辨率过滤规则（只保留1080p及以上） ==========
def is_hd_channel(name, url=""):
    """
    判断频道是否为高清（1080p及以上）
    规则：名称或URL中包含1080/4K/8K/2160等关键词，
          且不包含720/480/360等低分辨率标识。
    """
    text = (name + " " + url).lower()
    
    # 高清关键词（通过）
    hd_keywords = ["1080", "4k", "8k", "2160", "uhd", "超清", "高清"]
    # 低清关键词（直接过滤）
    sd_keywords = ["720", "480", "360", "标清", "流畅"]
    
    # 如果包含低清关键词且不包含高清关键词，则过滤
    if any(k in text for k in sd_keywords) and not any(k in text for k in hd_keywords):
        return False
    
    # 必须包含至少一个高清关键词，否则视为普通清晰度，过滤
    if not any(k in text for k in hd_keywords):
        return False
    
    return True

# ========== 原有功能函数（保持不动） ==========
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
    return 99 if ('4K' in name or '8K' in name) else 100

PROVINCE_ORDER = ["北京","天津","河北","山西","内蒙古","辽宁","吉林","黑龙江",
                  "上海","江苏","浙江","安徽","福建","江西","山东","河南","湖北",
                  "湖南","广东","广西","海南","重庆","四川","贵州","云南","陕西",
                  "甘肃","宁夏","新疆"]
def get_websort(name):
    for idx,p in enumerate(PROVINCE_ORDER):
        if p in name:
            return idx
    return 999

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

def safe_check(url):
    if not url.startswith("http"):
        return False
    if "m3u8" in url.lower() or "ts" in url.lower() or "live" in url.lower():
        return True
    try:
        res = requests.head(url, timeout=CHECK_TIMEOUT, allow_redirects=True, verify=False)
        return res.status_code in (200,301,302,304)
    except:
        return True

def parse_mix(lines):
    arr, seen_url = [], set()
    i=0
    while i < len(lines):
        t = lines[i]
        if "," in t and not t.startswith("#"):
            n,u = t.split(",",1)
            n,u = n.strip(),u.strip()
            if u.startswith("http") and u not in seen_url and n:
                seen_url.add(u)
                arr.append((n,u))
            i+=1
        elif t.startswith("#EXTINF") and i+1<len(lines):
            n = t.split(",")[-1].strip()
            u = lines[i+1].strip()
            if u.startswith("http") and u not in seen_url and n:
                seen_url.add(u)
                arr.append((n,u))
            i+=2
        else:
            i+=1
    return arr

def match_group(name):
    low = name.lower()
    for g in CATEGORIES:
        for k in g["kw"]:
            if k.lower() in low:
                return g["name"]
    return "其他频道"

def main():
    requests.packages.urllib3.disable_warnings()

    # 1. 拉取私源
    local = fetch_src(LOCAL_TXT) if os.path.exists(LOCAL_TXT) else []
    remote = fetch_src(OWN_REMOTE)
    my_private_src = local + remote
    print(f"✅你的私源总数：{len(my_private_src)}个")

    # 2. 拉取公共备用源
    backup_all = []
    for b in BACKUP_POOL:
        backup_all.extend(fetch_src(b))
    print(f"🔧公共备用源总数：{len(backup_all)}个")

    # 3. 合并解析（私源优先）
    raw = parse_mix(my_private_src + backup_all)
    print(f"📥合并后待处理总数：{len(raw)}个")

    # 4. 存活校验
    ok = []
    bad = 0
    with ThreadPoolExecutor(max_workers=10) as ex:
        task = {ex.submit(safe_check,u):(n,u) for n,u in raw}
        for f in as_completed(task):
            n,u = task[f]
            if f.result():
                ok.append((n,u))
            else:
                bad+=1
    print(f"✅存活校验后：{len(ok)}个 | ❌剔除无效链：{bad}个")

    # ========== 新增：只保留1080p及以上高清频道 ==========
    hd_list = []
    for n,u in ok:
        if is_hd_channel(n, u):
            hd_list.append((n,u))
    print(f"🎯筛选1080p+高清频道：{len(hd_list)}个")

    # ========== 分组排序 ==========
    bucket = {g["name"]:[] for g in CATEGORIES}
    bucket["其他频道"] = []
    for n,u in hd_list:
        bucket[match_group(n)].append((n,u))
    
    bucket["📺央视频道"].sort(key=lambda x:get_cctv_sort_key(x[0]))
    bucket["📺卫视频道"].sort(key=lambda x:get_websort(x[0]))

    # ========== 彻底覆盖生成新文件 ==========
    if os.path.exists(OUT_M3U):
        os.remove(OUT_M3U)
        print("🗑️ 旧iptv.m3u已删除")

    m3u = ['#EXTM3U x-tvg-url="https://epg.112114.xyz/epg.xml.gz"']
    order = [g["name"] for g in CATEGORIES] + ["其他频道"]
    for gname in order:
        for n,u in bucket[gname]:
            m3u.append(f'#EXTINF:-1 group-title="{gname}",{n}')
            m3u.append(u)

    with open(OUT_M3U,"w",encoding="utf-8") as f:
        f.write("\n".join(m3u)+"\n")

    # 日志记录
    log = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 私源优先｜总{len(raw)}｜存活{len(ok)}｜高清{len(hd_list)}\n"
    with open(LOG_TXT,"a",encoding="utf-8") as f:
        f.write(log)
    print(log + "🎉执行完毕：仅保留1080p+高清频道！")

if __name__ == "__main__":
    main()