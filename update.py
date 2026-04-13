import os
import re
import time
import requests
from datetime import datetime

# ===================== 配置区 =====================
CHECK_TIMEOUT = 8
LOCAL_TXT = "直播源.txt"
OUT_M3U = "直播汇总.m3u"
LOG_TXT = "更新日志.txt"

# 可用的网络源（你可以自己加）
NETWORK_SOURCES = [
    "https://raw.githubusercontent.com/longtian1024/iptv/main/tv.txt",
    "https://raw.githubusercontent.com/ssjunjie1/IPTV/main/IPTV.txt",
    "https://raw.githubusercontent.com/longg0201/iptv/main/tv.txt",
]

# 频道分类
CATEGORIES = {
    "📺央视频道": ["CCTV", "央视"],
    "📺卫视频道": ["卫视"],
    "🎥4K频道": ["4K", "4k", "8K", "8k", "UHD", "2160p"],
    "🎬影视频道": ["电影", "影院", "影视"],
    "🧒少儿频道": ["少儿", "动画", "儿童"],
    "🇭🇰香港频道": ["TVB", "翡翠", "香港"],
    "其他频道": []
}

# 卫视排序
PROVINCE_ORDER = [
    "北京", "天津", "河北", "山西", "内蒙古",
    "辽宁", "吉林", "黑龙江", "上海", "江苏",
    "浙江", "安徽", "福建", "江西", "山东",
    "河南", "湖北", "湖南", "广东", "广西", "海南",
    "重庆", "四川", "贵州", "云南", "西藏",
    "陕西", "甘肃", "青海", "宁夏", "新疆"
]

# ===================== 工具函数 =====================

def clean_name(name):
    name = re.sub(r'[\[\(（【].*?[\]\)）】]', '', name)
    name = re.sub(r'\b\d+[Pp]\b', '', name)
    name = re.sub(r'\b(4K|8K|HD|高清|超清|标清)\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def get_key(name):
    cn = clean_name(name)
    return re.sub(r'[^\w\u4e00-\u9fff]', '', cn).lower()

def check_alive(url):
    try:
        r = requests.head(url, timeout=CHECK_TIMEOUT)
        return r.status_code in (200, 302)
    except:
        try:
            r = requests.get(url, timeout=CHECK_TIMEOUT, stream=True)
            return r.status_code in (200, 302)
        except:
            return False

def fetch_network_sources():
    channels = {}
    for url in NETWORK_SOURCES:
        try:
            r = requests.get(url, timeout=10)
            lines = r.text.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue
                if "," in line:
                    parts = line.split(",", 1)
                    if len(parts) == 2:
                        name, u = parts[0].strip(), parts[1].strip()
                        if u.startswith("http"):
                            key = get_key(name)
                            if key not in channels:
                                channels[key] = (name, u)
                    i += 1
                elif line.startswith("#EXTINF"):
                    name = line.split(",")[-1].strip()
                    if i + 1 < len(lines):
                        u = lines[i + 1].strip()
                        if u.startswith("http"):
                            key = get_key(name)
                            if key not in channels:
                                channels[key] = (name, u)
                        i += 2
                    else:
                        i += 1
                else:
                    i += 1
        except Exception as e:
            continue
    return channels

def get_category(name):
    for cat, kw in CATEGORIES.items():
        if cat == "其他频道": continue
        for k in kw:
            if k.lower() in name.lower():
                return cat
    return "其他频道"

def sort_key(name, cat):
    if cat == "📺央视频道":
        m = re.search(r'CCTV[-]?(\d+)', name)
        return int(m.group(1)) if m else 99
    elif cat == "📺卫视频道":
        for idx, p in enumerate(PROVINCE_ORDER):
            if p in name:
                return idx
    return 999

# ===================== 主逻辑 =====================

def main():
    start = time.time()
    print("🚀 开始更新直播源")

    # 1. 读取本地
    local = {}
    if os.path.exists(LOCAL_TXT):
        try:
            with open(LOCAL_TXT, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except:
            with open(LOCAL_TXT, "r", encoding="gbk") as f:
                lines = f.readlines()

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "," in line:
                parts = line.split(",", 1)
                if len(parts) == 2:
                    name, url = parts[0].strip(), parts[1].strip()
                    if url.startswith("http"):
                        key = get_key(name)
                        local[key] = (name, url)

    print(f"📂 本地频道总数：{len(local)}")

    # 2. 检测本地可用/不可用
    valid = {}
    invalid_keys = []
    for key, (name, url) in local.items():
        if check_alive(url):
            valid[key] = (name, url)
        else:
            invalid_keys.append(key)

    print(f"✅ 本地可用：{len(valid)} 个")
    print(f"❌ 本地失效：{len(invalid_keys)} 个")

    # 3. 失效的从网络补充
    replaced = 0
    if invalid_keys:
        print("🌐 正在从网络抓取补充源...")
        net_channels = fetch_network_sources()
        for key in invalid_keys:
            if key in net_channels:
                n_name, n_url = net_channels[key]
                if check_alive(n_url):
                    valid[key] = (n_name, n_url)
                    replaced += 1

    print(f"🔄 已补充失效频道：{replaced} 个")

    # 4. 保存回本地
    with open(LOCAL_TXT, "w", encoding="utf-8") as f:
        for name, url in valid.values():
            f.write(f"{name},{url}\n")

    # 5. 分类排序
    groups = {c: [] for c in CATEGORIES}
    for name, url in valid.values():
        cat = get_category(name)
        groups[cat].append((name, url))

    for cat in groups:
        groups[cat].sort(key=lambda x: sort_key(x[0], cat))

    # 6. 输出M3U
    with open(OUT_M3U, "w", encoding="utf-8") as f:
        f.write('#EXTM3U x-tvg-url="https://epg.112114.xyz/epg.xml.gz"\n')
        for cat in CATEGORIES:
            for name, url in groups[cat]:
                f.write(f'#EXTINF:-1 group-title="{cat}",{name}\n{url}\n')

    # 日志
    cost = time.time() - start
    log = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 总频道:{len(valid)} 可用:{len(valid)-replaced} 补充:{replaced} 耗时:{cost:.1f}s\n"
    with open(LOG_TXT, "a", encoding="utf-8") as f:
        f.write(log)

    print("\n🎉 完成！")
    print(log.strip())

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    main()
