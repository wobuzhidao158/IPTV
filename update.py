import os
import re
import time
import requests
from datetime import datetime

# ===================== 配置区 =====================
CHECK_TIMEOUT = 10
LOCAL_TXT = "直播源.txt"
OUT_M3U = "直播汇总.m3u"
LOG_TXT = "更新日志.txt"

NETWORK_SOURCES = [
    "https://your-api-1.com/iptv.txt",
    "https://your-api-2.com/iptv.txt",
    "https://your-api-3.com/iptv.m3u",
]

CATEGORIES = {
    "📺央视频道": ["CCTV", "央视"],
    "📺卫视频道": ["卫视"],
    "🎥4K频道": ["4K", "4k", "8K", "8k", "UHD"],
    "🎬影视频道": ["电影", "影院", "影视"],
    "其他频道": []
}

PROVINCE_ORDER = [
    "北京", "天津", "河北", "山西", "内蒙古",
    "辽宁", "吉林", "黑龙江", "上海", "江苏",
    "浙江", "安徽", "福建", "江西", "山东",
    "河南", "湖北", "湖南", "广东", "广西", "海南",
    "重庆", "四川", "贵州", "云南", "西藏",
    "陕西", "甘肃", "青海", "宁夏", "新疆"
]

# ===================== 核心函数 =====================

def clean_name(name):
    name = re.sub(r'[\[\(（【].*?[\]\)）】]', '', name)
    name = re.sub(r'\b\d+[Pp]\b', '', name)
    name = re.sub(r'\b(4K|8K|HD|FHD|UHD|SD|高清|超清|标清)\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\b(IPV4|IPV6|Not24/7|24/7)\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def get_key(name):
    name = clean_name(name)
    return re.sub(r'[^\w\u4e00-\u9fff]', '', name).lower()

def check_alive(url):
    return True  # 永远返回有效，不检测

def fetch_sources(url):
    sources = []
    try:
        r = requests.get(url, timeout=8)
        lines = r.text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith('#'):
                i += 1
                continue
            if ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2:
                    name, url = parts[0].strip(), parts[1].strip()
                    sources.append((name, url))
                i += 1
            elif line.startswith('#EXTINF'):
                name = line.split(',')[-1].strip()
                if i + 1 < len(lines):
                    url = lines[i+1].strip()
                    sources.append((name, url))
                    i += 2
                else:
                    i += 1
            else:
                i += 1
    except:
        pass
    return sources

def get_category(name):
    for cat, keywords in CATEGORIES.items():
        if cat == "其他频道":
            continue
        for kw in keywords:
            if kw.lower() in name.lower():
                return cat
    return "其他频道"

def sort_key(name, cat):
    if cat == "📺央视频道":
        m = re.search(r'CCTV[-]?(\d+)', name)
        return m and int(m.group(1)) or 99
    elif cat == "📺卫视频道":
        for i, p in enumerate(PROVINCE_ORDER):
            if p in name:
                return i
    return 999

# ===================== 主程序 =====================

def main():
    start = time.time()
    print("🚀 开始更新...")

    # 1. 读取本地源（兼容所有格式，不去重）
    valid = []
    if os.path.exists(LOCAL_TXT):
        try:
            with open(LOCAL_TXT, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except:
            with open(LOCAL_TXT, 'r', encoding='gbk') as f:
                lines = f.readlines()

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    url = parts[1].strip()
                    valid.append((clean_name(name), url))

    print(f"📂 本地源读取: {len(valid)} 个")

    # 2. 保存回本地（保留所有）
    with open(LOCAL_TXT, 'w', encoding='utf-8') as f:
        for name, url in valid:
            f.write(f"{name},{url}\n")

    # 3. 分类
    categories = {cat: [] for cat in CATEGORIES.keys()}
    for name, url in valid:
        cat = get_category(name)
        categories[cat].append((name, url))

    # 4. 排序
    for cat in categories:
        categories[cat].sort(key=lambda x: sort_key(x[0], cat))

    # 5. 输出M3U
    with open(OUT_M3U, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for cat in CATEGORIES.keys():
            if categories[cat]:
                for name, url in categories[cat]:
                    f.write(f'#EXTINF:-1 group-title="{cat}",{name}\n{url}\n')

    # 6. 日志
    elapsed = time.time() - start
    log = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 频道总数: {len(valid)} | 耗时: {elapsed:.1f}s\n"
    with open(LOG_TXT, 'a', encoding='utf-8') as f:
        f.write(log)

    print(f"\n🎉 {log.strip()}")
    print(f"✅ 已生成: {OUT_M3U}")

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    main()
