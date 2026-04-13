import os
import re
import time
import requests
from datetime import datetime
from collections import defaultdict

# ===================== 配置区 =====================
MIN_RESOLUTION_SCORE = 70
CHECK_TIMEOUT = 3
LOCAL_TXT = "直播源.txt"
OUT_M3U = "直播汇总.m3u"
LOG_TXT = "更新日志.txt"

# 网络源接口（请替换为你的真实API地址）
NETWORK_SOURCES = [
    "https://your-api-1.com/iptv.txt",
    "https://your-api-2.com/iptv.m3u",
]

# ===================== 频道分类配置 =====================
CATEGORIES = [
    {"name": "📺央视频道", "kw": ["CCTV", "央视"]},
    {"name": "📺卫视频道", "kw": ["卫视"]},
    {"name": "🎥4K频道", "kw": ["4k", "8k", "uhd", "4K"]},
    {"name": "🎬影视频道", "kw": ["电影", "影院", "影视"]},
    {"name": "👦少儿频道", "kw": ["少儿", "儿童", "卡通"]},
    {"name": "🇭🇰香港频道", "kw": ["香港", "TVB", "翡翠"]},
    {"name": "🇲🇴澳门频道", "kw": ["澳门"]},
    {"name": "🌍台湾频道", "kw": ["台湾", "中天", "东森"]},
    {"name": "🇸🇬新加坡频道", "kw": ["新加坡", "新传媒"]},
    {"name": "🎬影视轮播", "kw": ["轮播"]},
]

PROVINCE_ORDER = [
    "北京", "天津", "河北", "山西", "内蒙古",
    "辽宁", "吉林", "黑龙江",
    "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东",
    "河南", "湖北", "湖南", "广东", "广西", "海南",
    "重庆", "四川", "贵州", "云南", "西藏",
    "陕西", "甘肃", "青海", "宁夏", "新疆"
]

# ===================== 工具函数 =====================
def clean_channel_name(name):
    """
    彻底清理频道名，只保留纯净名称
    移除所有括号、分辨率、IPV4、Not24/7等标记
    """
    # 1. 移除各种括号及其内容
    name = re.sub(r'[\[\(（【].*?[\]\)）】]', '', name)
    
    # 2. 移除分辨率标记（1080p、720p、4K、HD等）
    name = re.sub(r'\b\d+[Pp]\b', '', name)
    name = re.sub(r'\b(4K|8K|HD|FHD|UHD|SD|高清|超清|标清)\b', '', name, flags=re.IGNORECASE)
    
    # 3. 移除特殊标记
    name = re.sub(r'\b(IPV4|IPV6|IPV4/IPV6)\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\[Not24/7\]', '', name, flags=re.IGNORECASE)
    name = re.sub(r'Not24/7', '', name, flags=re.IGNORECASE)
    name = re.sub(r'24/7', '', name)
    
    # 4. 移除数字后缀（如 "综合1"、"新闻2"）
    name = re.sub(r'\d+$', '', name)
    
    # 5. 移除多余的空格和符号
    name = re.sub(r'[_\-\s]+', ' ', name)
    name = name.strip()
    
    # 6. 移除前后可能残留的符号
    name = re.sub(r'^[\s\-_]+|[\s\-_]+$', '', name)
    
    return name

def normalize_name(name):
    """标准化频道名用于去重"""
    name = clean_channel_name(name)
    return re.sub(r'[^\w\u4e00-\u9fff]', '', name).lower()

def get_cctv_sort_key(name):
    """央视排序"""
    m = re.search(r'CCTV[-]?(\d+)', name)
    if m:
        num = int(m.group(1))
        return num + 0.5 if '+' in name else num
    alias = {"一套":1, "二套":2, "三套":3, "四套":4, "五套":5,
             "六套":6, "七套":7, "八套":8, "九套":9, "十套":10}
    for a, n in alias.items():
        if a in name:
            return n
    return 99

def get_websort(name):
    """卫视排序"""
    for idx, p in enumerate(PROVINCE_ORDER):
        if p in name:
            return idx
    return 999

def match_group(name):
    """频道分类"""
    low = name.lower()
    for g in CATEGORIES:
        for k in g["kw"]:
            if k.lower() in low:
                return g["name"]
    return "其他频道"

def cut_lines(text):
    """分割文本行"""
    return [x.strip() for x in text.splitlines() if x.strip()]

def fetch_url_content(url):
    """获取远程内容"""
    try:
        r = requests.get(url, timeout=8, verify=False)
        r.encoding = 'utf-8'
        return cut_lines(r.text)
    except:
        return []

def parse_sources(lines):
    """解析直播源"""
    sources = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith('#'):
            i += 1
            continue
        
        if ',' in line and not line.startswith('#'):
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
    return sources

def extract_resolution(name, url):
    """提取分辨率分数"""
    text = (name + url).lower()
    if '8k' in text or '4320' in text:
        return 100
    elif '4k' in text or '2160' in text or 'uhd' in text:
        return 85
    elif '1080' in text or 'fhd' in text:
        return 70
    elif '720' in text or 'hd' in text:
        return 50
    return 40

def is_alive(url):
    """检测源是否存活"""
    try:
        r = requests.get(url, timeout=CHECK_TIMEOUT, stream=True, verify=False)
        return r.status_code == 200
    except:
        return False

def is_qualified(name, url):
    """检测源是否合格"""
    if not is_alive(url):
        return False
    return extract_resolution(name, url) >= MIN_RESOLUTION_SCORE

# ===================== 主函数 =====================
def main():
    start_time = time.time()
    print("🚀 开始更新直播源...")
    
    # 1. 读取本地源
    local_sources = {}
    if os.path.exists(LOCAL_TXT):
        with open(LOCAL_TXT, 'r', encoding='utf-8') as f:
            for line in cut_lines(f.read()):
                if ',' in line:
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        name = clean_channel_name(parts[0].strip())
                        url = parts[1].strip()
                        if url.startswith('http') and name:
                            key = normalize_name(name)
                            local_sources[key] = (name, url)
    print(f"📂 读取本地源: {len(local_sources)} 个")
    
    # 2. 检测本地源
    valid_local = {}
    need_replace = []
    
    for key, (name, url) in local_sources.items():
        if is_alive(url):
            valid_local[key] = (name, url)
        else:
            need_replace.append(key)
    
    print(f"✅ 本地源有效: {len(valid_local)} | 失效: {len(need_replace)}")
    
    # 3. 从网络抓取新源
    network_sources = {}
    if need_replace:
        print("🌐 从网络抓取新源...")
        all_lines = []
        for src in NETWORK_SOURCES:
            all_lines.extend(fetch_url_content(src))
        
        for name, url in parse_sources(all_lines):
            clean_name = clean_channel_name(name)
            if not clean_name:
                continue
            key = normalize_name(clean_name)
            if key in need_replace and key not in network_sources:
                if is_qualified(clean_name, url):
                    network_sources[key] = (clean_name, url)
        
        print(f"📡 抓取到新源: {len(network_sources)} 个")
    
    # 4. 合并结果
    final_sources = dict(valid_local)
    for key, value in network_sources.items():
        final_sources[key] = value
    
    # 5. 保存更新后的本地源
    with open(LOCAL_TXT, 'w', encoding='utf-8') as f:
        for name, url in final_sources.values():
            f.write(f"{name},{url}\n")
    
    print(f"💾 已更新本地源: {len(final_sources)} 个频道")
    
    # 6. 分类并排序
    bucket = {g["name"]: [] for g in CATEGORIES}
    bucket["其他频道"] = []
    
    for name, url in final_sources.values():
        bucket[match_group(name)].append((name, url))
    
    bucket["📺央视频道"].sort(key=lambda x: get_cctv_sort_key(x[0]))
    bucket["📺卫视频道"].sort(key=lambda x: get_websort(x[0]))
    
    # 7. 写入M3U文件
    with open(OUT_M3U, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for gname in [g["name"] for g in CATEGORIES] + ["其他频道"]:
            if bucket[gname]:
                for name, url in bucket[gname]:
                    f.write(f'#EXTINF:-1 group-title="{gname}",{name}\n{url}\n')
    
    # 8. 写入日志
    elapsed = time.time() - start_time
    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 更新完成 | 总频道: {len(final_sources)} | 本地保留: {len(valid_local)} | 网络替换: {len(network_sources)} | 耗时: {elapsed:.2f}s\n"
    
    with open(LOG_TXT, 'a', encoding='utf-8') as f:
        f.write(log_msg)
    
    print(f"\n🎉 {log_msg.strip()}")

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    main()