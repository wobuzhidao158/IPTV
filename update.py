import os
import re
import time
import requests
from datetime import datetime

# ===================== 配置区 =====================
CHECK_TIMEOUT = 10             # 🔧 修改1：检测超时改为10秒（原为3秒）
LOCAL_TXT = "直播源.txt"        # 本地源文件
OUT_M3U = "直播汇总.m3u"        # 输出文件
LOG_TXT = "更新日志.txt"        # 日志文件

# 网络源地址（按优先级排序）
NETWORK_SOURCES = [
    "https://your-api-1.com/iptv.txt",   # 主用地址（请替换为真实地址）
    "https://your-api-2.com/iptv.txt",   # 备用地址1
    "https://your-api-3.com/iptv.m3u",   # 备用地址2
]

# 频道分类
CATEGORIES = {
    "📺央视频道": ["CCTV", "央视"],
    "📺卫视频道": ["卫视"],
    "🎥4K频道": ["4K", "4k", "8K", "8k", "UHD"],
    "🎬影视频道": ["电影", "影院", "影视"],
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

# ===================== 核心函数 =====================

def clean_name(name):
    """清理频道名 - 只保留纯净名称"""
    name = re.sub(r'[\[\(（【].*?[\]\)）】]', '', name)
    name = re.sub(r'\b\d+[Pp]\b', '', name)
    name = re.sub(r'\b(4K|8K|HD|FHD|UHD|SD|高清|超清|标清)\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\b(IPV4|IPV6|Not24/7|24/7)\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def get_key(name):
    """生成唯一标识"""
    name = clean_name(name)
    return re.sub(r'[^\w\u4e00-\u9fff]', '', name).lower()

def check_alive(url):
    """快速检测源是否存活（使用配置的CHECK_TIMEOUT）"""
    try:
        r = requests.get(url, timeout=CHECK_TIMEOUT, stream=True)
        return r.status_code == 200
    except:
        return False

def fetch_sources(url):
    """从网络抓取源（抓取超时固定8秒，避免卡死）"""
    sources = []
    try:
        r = requests.get(url, timeout=8)  # 抓取地址本身超时保持8秒
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
                    if url.startswith('http'):
                        sources.append((name, url))
                i += 1
            elif line.startswith('#EXTINF'):
                name = line.split(',')[-1].strip()
                if i + 1 < len(lines):
                    url = lines[i + 1].strip()
                    if url.startswith('http'):
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
    """获取频道分类"""
    for cat, keywords in CATEGORIES.items():
        if cat == "其他频道":
            continue
        for kw in keywords:
            if kw.lower() in name.lower():
                return cat
    return "其他频道"

def sort_key(name, cat):
    """排序规则"""
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
    
    # 1. 读取本地源
    local_sources = {}
    if os.path.exists(LOCAL_TXT):
        with open(LOCAL_TXT, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if ',' in line:
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        name, url = parts[0].strip(), parts[1].strip()
                        if url.startswith('http'):
                            key = get_key(name)
                            local_sources[key] = (clean_name(name), url)
    print(f"📂 本地源: {len(local_sources)} 个")
    
    # 2. 检测本地源，分类有效/失效（使用10秒超时）
    valid = {}
    invalid_keys = []
    
    for key, (name, url) in local_sources.items():
        if check_alive(url):   # 此处使用 CHECK_TIMEOUT=10 秒
            valid[key] = (name, url)
        else:
            invalid_keys.append(key)
    
    print(f"✅ 有效: {len(valid)} | ❌ 失效: {len(invalid_keys)}")
    
    # 3. 为失效频道抓取新源
    replaced = 0
    if invalid_keys:
        print("🌐 抓取新源...")
        network_sources = {}
        
        for api in NETWORK_SOURCES:
            for name, url in fetch_sources(api):
                key = get_key(name)
                if key in invalid_keys and key not in network_sources:
                    if check_alive(url):   # 新源也用10秒检测
                        network_sources[key] = (clean_name(name), url)
        
        for key in invalid_keys:
            if key in network_sources:
                valid[key] = network_sources[key]
                replaced += 1
        
        print(f"🔄 替换成功: {replaced} 个")
    
    # 4. 保存更新后的本地源
    with open(LOCAL_TXT, 'w', encoding='utf-8') as f:
        for name, url in valid.values():
            f.write(f"{name},{url}\n")
    
    # 5. 分类
    categories = {cat: [] for cat in CATEGORIES.keys()}
    for name, url in valid.values():
        cat = get_category(name)
        categories[cat].append((name, url))
    
    # 6. 排序
    for cat in categories:
        categories[cat].sort(key=lambda x: sort_key(x[0], cat))
    
    # 7. 输出M3U
    with open(OUT_M3U, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for cat in CATEGORIES.keys():
            if categories[cat]:
                for name, url in categories[cat]:
                    f.write(f'#EXTINF:-1 group-title="{cat}",{name}\n{url}\n')
    
    # 8. 日志
    elapsed = time.time() - start
    log = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 频道: {len(valid)} | 有效: {len(valid)-replaced} | 替换: {replaced} | 耗时: {elapsed:.1f}s\n"
    
    with open(LOG_TXT, 'a', encoding='utf-8') as f:
        f.write(log)
    
    print(f"\n🎉 {log.strip()}")

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    main()