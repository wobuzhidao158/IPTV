# -*- coding: utf-8 -*-
# 私源绝对优先终版｜不分地区｜全频道保留｜彻底覆盖｜你的源永不被顶替
import os
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# ========== 基础配置（你的私源永远优先） ==========
LOCAL_TXT = "直播源.txt"          # 你的本地私源
OWN_REMOTE = "https://zhibo.cc.cd/api.php?token=BVna62di&type=txt"  # 你的API私源
OUT_M3U = "iptv.m3u"
LOG_TXT = "update_log.txt"
# 【核心：只做基础存活校验，不做地区限制，不杀你的源】
CHECK_TIMEOUT = 8
BACKUP_POOL = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u"
]
# =====================================================

# 央视精准排序（100%锁死顺序，不打乱你的源）
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

# 卫视省份标准排序
PROVINCE_ORDER = ["北京","天津","河北","山西","内蒙古","辽宁","吉林","黑龙江",
                  "上海","江苏","浙江","安徽","福建","江西","山东","河南","湖北",
                  "湖南","广东","广西","海南","重庆","四川","贵州","云南","陕西",
                  "甘肃","宁夏","新疆"]
def get_websort(name):
    for idx,p in enumerate(PROVINCE_ORDER):
        if p in name:
            return idx
    return 999

# 【全分类完整保留：港澳台/新加坡/影视轮播一个不少】
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

# 【核心校验：只做基础存活，不做地区限制，不杀你的源】
def safe_check(url):
    if not url.startswith("http"):
        return False
    # 直播流格式直接放行，100%保住你的源
    if "m3u8" in url.lower() or "ts" in url.lower() or "live" in url.lower():
        return True
    # 普通链接宽松校验，不卡死
    try:
        res = requests.head(url, timeout=CHECK_TIMEOUT, allow_redirects=True, verify=False)
        return res.status_code in (200,301,302,304)
    except:
        # 超时不判死，直接放行，不丢你的台
        return True

# 双格式解析+去重（先入先保，你的源永远优先，公共源不顶替）
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

    # ============== 【绝对核心：你的私源100%优先】 ==============
    # 1. 先拉取你的所有私源（本地+API），优先级最高
    local = fetch_src(LOCAL_TXT) if os.path.exists(LOCAL_TXT) else []
    remote = fetch_src(OWN_REMOTE)
    my_private_src = local + remote
    print(f"✅你的私源总数：{len(my_private_src)}个")

    # 2. 再拉取公共备用源，只补你没有的，绝不抢位
    backup_all = []
    for b in BACKUP_POOL:
        backup_all.extend(fetch_src(b))
    print(f"🔧公共备用源总数：{len(backup_all)}个")

    # 3. 顺序锁死：你的私源在前，公共源在后
    # 去重时先入先保，你的源永远保留，公共源重复直接丢弃
    raw = parse_mix(my_private_src + backup_all)
    print(f"📥合并后待处理总数：{len(raw)}个")

    # ============== 宽松校验，不杀你的源 ==============
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
    print(f"✅最终存活：{len(ok)}个 | ❌仅剔除彻底无效死链：{bad}个")

    # ============== 分组排序，不打乱你的源结构 ==============
    bucket = {g["name"]:[] for g in CATEGORIES}
    bucket["其他频道"] = []
    for item in ok:
        bucket[match_group(item[0])].append(item)
    # 仅对央视/卫视做规整排序，不影响你的源优先级
    bucket["📺央视频道"].sort(key=lambda x:get_cctv_sort_key(x[0]))
    bucket["📺卫视频道"].sort(key=lambda x:get_websort(x[0]))

    # ============== 【彻底覆盖：先删旧文件，再写新文件】 ==============
    if os.path.exists(OUT_M3U):
        os.remove(OUT_M3U)
        print("🗑️ 旧iptv.m3u已彻底删除，准备全新覆盖生成")

    # 生成标准M3U
    m3u = ['#EXTM3U x-tvg-url="https://epg.112114.xyz/epg.xml.gz"']
    order = [g["name"] for g in CATEGORIES] + ["其他频道"]
    for gname in order:
        for n,u in bucket[gname]:
            m3u.append(f'#EXTINF:-1 group-title="{gname}",{n}')
            m3u.append(u)

    # 写入全新文件
    with open(OUT_M3U,"w",encoding="utf-8") as f:
        f.write("\n".join(m3u)+"\n")

    # 日志记录
    log = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 私源优先终版｜私源{len(my_private_src)}｜总{len(raw)}｜存活{len(ok)}\n"
    with open(LOG_TXT,"a",encoding="utf-8") as f:
        f.write(log)
    print(log + "🎉执行完毕：你的源绝对优先，不分地区，全频道保留，彻底覆盖无残留！")

if __name__ == "__main__":
    main()
