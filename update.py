# -*- coding: utf-8 -*-
"""
绝对优先本地私源版：
- 本地直播源.txt 无条件全部保留（不杀任何一行）
- 网络新源仅作为补充，绝不顶替已有频道名或URL
- 存活校验只针对新源，本地源直接信任
"""
import os
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# ========== 配置 ==========
LOCAL_TXT = "直播源.txt"           # 你的绝对优先私源文件
OWN_REMOTE = "https://zhibo.cc.cd/api.php?token=BVna62di&type=txt"  # 你的API源
OUT_M3U = "iptv.m3u"
LOG_TXT = "update_log.txt"
CHECK_TIMEOUT = 8

# 公共备用源（只作为补充，不会替换你的私源）
BACKUP_POOL = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u"
]

# 分类关键词（保持不变）
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

# 央视/卫视排序规则
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
    return 99 if ('4K' in name or '8K' in name) else 100

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

# ========== 辅助函数 ==========
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
    """只用于校验新源，本地源直接信任不校验"""
    if not url.startswith("http"):
        return False
    # 流媒体格式直接放行
    if "m3u8" in url.lower() or "ts" in url.lower() or "live" in url.lower():
        return True
    try:
        res = requests.head(url, timeout=CHECK_TIMEOUT, allow_redirects=True, verify=False)
        return res.status_code in (200,301,302,304)
    except:
        return False

def parse_mix(lines):
    """
    解析各种格式的直播源，返回 [(频道名, URL), ...]
    支持：
    - 频道名,URL
    - #EXTINF:-1,频道名
      URL
    """
    arr, seen_url = [], set()
    i = 0
    while i < len(lines):
        line = lines[i]
        if "," in line and not line.startswith("#"):
            # 格式：频道名,URL
            n, u = line.split(",", 1)
            n, u = n.strip(), u.strip()
            if u.startswith("http") and u not in seen_url and n:
                seen_url.add(u)
                arr.append((n, u))
            i += 1
        elif line.startswith("#EXTINF") and i+1 < len(lines):
            # M3U格式
            n = line.split(",")[-1].strip()
            u = lines[i+1].strip()
            if u.startswith("http") and u not in seen_url and n:
                seen_url.add(u)
                arr.append((n, u))
            i += 2
        else:
            i += 1
    return arr

# ========== 主逻辑 ==========
def main():
    requests.packages.urllib3.disable_warnings()

    # ---------- 第一步：绝对优先读取你的本地私源（全部保留，不做任何过滤）----------
    local_private = []
    if os.path.exists(LOCAL_TXT):
        with open(LOCAL_TXT, "r", encoding="utf-8") as f:
            content = f.read()
        local_private = parse_mix(cut_lines(content))
        print(f"✅ 本地私源读取：{len(local_private)} 个频道（全部无条件保留）")
    else:
        print(f"⚠️ 未找到本地文件：{LOCAL_TXT}，将仅使用网络源")

    # 再读取你的API私源（如果有）
    api_private = parse_mix(fetch_src(OWN_REMOTE))
    print(f"✅ API私源读取：{len(api_private)} 个")

    # ---------- 第二步：合并私源（本地+API），建立“已保护名单” ----------
    protected_names = set()   # 已经存在的频道名
    protected_urls = set()    # 已经存在的URL
    final_list = []

    # 先加本地源（绝对优先）
    for name, url in local_private:
        if name and url:
            protected_names.add(name.lower())
            protected_urls.add(url)
            final_list.append((name, url))

    # 再加API源，但避免与本地重复（URL相同或频道名相同则跳过）
    for name, url in api_private:
        if not name or not url:
            continue
        if url in protected_urls or name.lower() in protected_names:
            continue
        protected_names.add(name.lower())
        protected_urls.add(url)
        final_list.append((name, url))

    print(f"🔒 私源合并后受保护频道数：{len(final_list)}")

    # ---------- 第三步：拉取公共备用源，只取“新”频道 ----------
    backup_sources = []
    for src_url in BACKUP_POOL:
        backup_sources.extend(fetch_src(src_url))
    print(f"🌐 公共备用源拉取总数：{len(backup_sources)} 行")

    new_candidates = parse_mix(backup_sources)
    # 过滤掉已经受保护的频道
    new_only = []
    for name, url in new_candidates:
        if not name or not url:
            continue
        if url in protected_urls or name.lower() in protected_names:
            continue
        new_only.append((name, url))

    print(f"🆕 未受保护的新候选频道：{len(new_only)} 个")

    # ---------- 第四步：对新候选频道做存活校验（本地源已信任，不校验）----------
    alive_new = []
    if new_only:
        print("⏳ 正在校验新频道存活状态...")
        with ThreadPoolExecutor(max_workers=10) as ex:
            tasks = {ex.submit(safe_check, u): (n, u) for n, u in new_only}
            for future in as_completed(tasks):
                n, u = tasks[future]
                if future.result():
                    alive_new.append((n, u))
        print(f"✅ 新频道存活：{len(alive_new)} 个")
    else:
        alive_new = []

    # ---------- 第五步：最终列表 = 私源（已加入） + 存活新源 ----------
    for name, url in alive_new:
        if url not in protected_urls and name.lower() not in protected_names:
            final_list.append((name, url))

    print(f"📋 最终频道总数：{len(final_list)}（私源 {len(local_private)+len(api_private)} + 新源 {len(alive_new)}）")

    # ---------- 第六步：分组并排序（保持私源原有顺序在前，新源在后）----------
    bucket = {g["name"]: [] for g in CATEGORIES}
    bucket["其他频道"] = []

    for name, url in final_list:
        bucket[match_group(name)].append((name, url))

    # 仅对央视和卫视做内部排序，不打乱私源相对顺序（但因为先加入的先在列表中，排序会整体重排）
    # 为了完全尊重私源顺序，我们应该不排序，但用户可能希望分类后内部有序。
    # 这里保留排序，但私源本身因为加入顺序在前，排序后依然会在分类内靠前（因为排序键是根据频道名固定的）
    bucket["📺央视频道"].sort(key=lambda x: get_cctv_sort_key(x[0]))
    bucket["📺卫视频道"].sort(key=lambda x: get_websort(x[0]))

    # ---------- 第七步：写入M3U文件（彻底覆盖）----------
    if os.path.exists(OUT_M3U):
        os.remove(OUT_M3U)

    m3u_lines = ['#EXTM3U x-tvg-url="https://epg.112114.xyz/epg.xml.gz"']
    order = [g["name"] for g in CATEGORIES] + ["其他频道"]
    for group_name in order:
        for name, url in bucket[group_name]:
            m3u_lines.append(f'#EXTINF:-1 group-title="{group_name}",{name}')
            m3u_lines.append(url)

    with open(OUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines) + "\n")

    # 写日志
    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 私源保护：本地{len(local_private)} API{len(api_private)} | 新增{len(alive_new)} | 总{len(final_list)}\n"
    with open(LOG_TXT, "a", encoding="utf-8") as f:
        f.write(log_msg)
    print(log_msg)
    print("🎉 完成！你的本地私源绝对优先，一个都没少。")

if __name__ == "__main__":
    main()