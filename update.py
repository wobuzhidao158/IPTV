import os
import re
import time
import requests
from datetime import datetime
from collections import defaultdict

# ===================== 配置区（可根据需要修改）=====================
# 最低分辨率分数：70对应1080p，85对应4K，100对应8K
MIN_RESOLUTION_SCORE = 70
# 存活检测超时时间（秒）
CHECK_TIMEOUT = 5
# 本地源文件路径
LOCAL_TXT = "本地直播源.txt"
# 输出M3U文件路径
OUT_M3U = "直播汇总.m3u"
# 日志文件路径
LOG_TXT = "更新日志.txt"
# 备用公共源地址池（可自行添加/删除）
BACKUP_POOL = [
    # 示例公共源，可替换为你自己的源
    "https://example.com/iptv.txt",
    "https://example.com/iptv.m3u"
]
# ==================================================================

# 频道分类配置
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
    {"name": "🎬影视轮播", "kw": ["轮播", "影视轮播"]},
]

# 卫视频道排序顺序（按省份优先级）
PROVINCE_ORDER = [
    "北京", "天津", "河北", "山西", "内蒙古",
    "辽宁", "吉林", "黑龙江",
    "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东",
    "河南", "湖北", "湖南", "广东", "广西", "海南",
    "重庆", "四川", "贵州", "云南", "西藏",
    "陕西", "甘肃", "青海", "宁夏", "新疆"
]

# ===================== 工具函数区 =====================
def get_cctv_sort_key(name):
    """央视频道排序规则：按CCTV数字/一套二套等排序"""
    try:
        # 匹配CCTV-数字 或 CCTV数字
        m = re.search(r'CCTV[-]?(\d+)(\D|$)', name)
        if m:
            num = int(m.group(1))
            # 带+号的频道（如CCTV5+）排在对应数字后面
            return num + 0.5 if '+' in name else num
        
        # 匹配一套/二套等别名
        alias = {
            "一套":1, "二套":2, "三套":3, "四套":4, "五套":5,
            "六套":6, "七套":7, "八套":8, "九套":9, "十套":10,
            "十一套":11, "十二套":12, "十三套":13, "十四套":14,
            "十五套":15, "十六套":16, "十七套":17, "十八套":18
        }
        for a, n in alias.items():
            if a in name:
                return n
        return 99
    except:
        return 100

def get_websort(name):
    """卫视频道按PROVINCE_ORDER排序"""
    try:
        for idx, p in enumerate(PROVINCE_ORDER):
            if p in name:
                return idx
        return 999
    except:
        return 999

def match_group(name):
    """根据频道名匹配分类"""
    try:
        low = name.lower()
        # 优先匹配4K频道
        for k in CATEGORIES[2]["kw"]:
            if k in low:
                return "🎥4K频道"
        # 匹配其他分类
        for g in CATEGORIES:
            if g["name"] == "🎥4K频道":
                continue
            for k in g["kw"]:
                if k.lower() in low:
                    return g["name"]
        return "其他频道"
    except:
        return "其他频道"

def cut_lines(text):
    """按行分割并去除空行/首尾空格"""
    return [x.strip() for x in text.splitlines() if x.strip()]

def fetch_src(url):
    """获取远程源内容"""
    try:
        r = requests.get(url, timeout=10, verify=False)
        r.encoding = "utf-8"
        return cut_lines(r.text)
    except:
        return []

def parse_sources(lines, source_type="network"):
    """解析直播源，支持txt和m3u格式"""
    sources = []
    i = 0
    while i < len(lines):
        try:
            line = lines[i].strip()
            # 跳过空行、注释行
            if not line or line.startswith("#"):
                i += 1
                continue
            
            # 格式1：txt格式  频道名,url
            if "," in line and not line.startswith("#"):
                parts = line.split(",", 1)
                if len(parts) == 2:
                    name, url = parts[0].strip(), parts[1].strip()
                    if url.startswith("http"):
                        sources.append((name, url, source_type))
                i += 1
            
            # 格式2：m3u格式 #EXTINF:-1,频道名  下一行是url
            elif line.startswith("#EXTINF"):
                name = line.split(",")[-1].strip()
                if i+1 < len(lines):
                    url = lines[i+1].strip()
                    if url.startswith("http"):
                        sources.append((name, url, source_type))
                    i += 2
                else:
                    i += 1
            else:
                i += 1
        except:
            i += 1
    return sources

def extract_resolution(name, url):
    """提取分辨率分数，越高越清晰"""
    try:
        text = (name + " " + url).lower()
        if "8k" in text or "4320" in text:
            return 100
        elif "4k" in text or "2160" in text or "uhd" in text:
            return 85
        elif "1080" in text or "fhd" in text or "1920" in text:
            return 70
        elif "720" in text or "hd" in text or "1280" in text:
            return 50
        else:
            return 40
    except:
        return 40

def is_alive(url):
    """检测直播源是否存活"""
    try:
        r = requests.head(url, timeout=CHECK_TIMEOUT, verify=False)
        return r.status_code in (200, 301, 302, 403)
    except:
        return False

def is_network_qualified(name, url):
    """网络源校验：存活 + 满足最低分辨率（1080p）"""
    if not is_alive(url):
        return False
    res_score = extract_resolution(name, url)
    return res_score >= MIN_RESOLUTION_SCORE

def select_best_for_channel(candidates):
    """
    频道内择优：
    1. 优先从本地源中选（不做检测，直接信任，选第一个）
    2. 若没有本地源，则从网络源中选第一个满足条件的
    """
    local = [c for c in candidates if c[2] == "local"]
    network = [c for c in candidates if c[2] == "network"]
    
    if local:
        # 本地源无条件保留第一个
        return (local[0][0], local[0][1])
    
    # 没有本地源，筛选网络源
    for name, url, stype in network:
        if is_network_qualified(name, url):
            return (name, url)
    return None

def normalize_name(name):
    """标准化频道名，用于去重（去除括号、空格、特殊符号）"""
    try:
        # 去除括号、空格、特殊符号，统一小写
        return re.sub(r"\s*[\[\(]?(\d+)[\)\]]?\s*", r"\1", name).lower().strip()
    except:
        return name.lower().strip()

# ===================== 主函数 =====================
def main():
    start_time = time.time()
    print("🚀 开始本地源优先更新...")

    # 1. 加载本地源（无条件信任）
    local_sources = []
    if os.path.exists(LOCAL_TXT):
        try:
            with open(LOCAL_TXT, "r", encoding="utf-8") as f:
                lines = cut_lines(f.read())
                local_sources = parse_sources(lines, source_type="local")
            print(f"✅ 本地私源: {len(local_sources)} 个")
        except Exception as e:
            print(f"⚠️ 本地源读取失败: {e}")
    else:
        print("⚠️ 未找到本地直播源.txt")

    # 2. 加载API源（示例，可替换为你的API地址）
    api_sources = []
    # api_sources = parse_sources(fetch_src("你的API地址"), source_type="network")
    print(f"✅ API私源: {len(api_sources)} 个")

    # 3. 加载公共备用源
    backup_lines = []
    for src in BACKUP_POOL:
        backup_lines.extend(fetch_src(src))
    public_sources = parse_sources(backup_lines, source_type="network")
    print(f"🌐 公共备用: {len(public_sources)} 个")

    # 4. 合并分组（本地源优先加入，去重）
    groups = defaultdict(list)
    seen_urls = set()

    # 先加本地源
    for name, url, stype in local_sources:
        key = normalize_name(name)
        if url not in seen_urls:
            groups[key].append((name, url, stype))
            seen_urls.add(url)
    
    # 再加API源
    for name, url, stype in api_sources:
        key = normalize_name(name)
        if url not in seen_urls:
            groups[key].append((name, url, stype))
            seen_urls.add(url)
    
    # 最后加公共源
    for name, url, stype in public_sources:
        key = normalize_name(name)
        if url not in seen_urls:
            groups[key].append((name, url, stype))
            seen_urls.add(url)

    total = len(groups)
    print(f"📋 去重后频道数: {total}")

    # 5. 频道筛选（本地源优先且不检测）
    print("⚡ 频道筛选（本地源无条件保留）...")
    best_list = []
    local_used = 0
    network_used = 0
    discarded = 0
    processed = 0

    for base, cands in groups.items():
        processed += 1
        if processed % 100 == 0:
            print(f"  进度: {processed}/{total}")
        
        best = select_best_for_channel(cands)
        if best:
            best_list.append(best)
            # 判断最终用的是本地还是网络
            is_local = any(c[2] == "local" for c in cands)
            if is_local:
                local_used += 1
            else:
                network_used += 1
        else:
            discarded += 1

    print(f"\n✅ 保留 {len(best_list)} 个频道 | 本地源: {local_used} | 网络源: {network_used} | 丢弃: {discarded}")

    # 6. 分组排序
    bucket = {g["name"]: [] for g in CATEGORIES}
    bucket["其他频道"] = []

    for name, url in best_list:
        bucket[match_group(name)].append((name, url))
    
    # 央视按数字排序，卫视按省份排序
    try:
        bucket["📺央视频道"].sort(key=lambda x: get_cctv_sort_key(x[0]))
        bucket["📺卫视频道"].sort(key=lambda x: get_websort(x[0]))
    except:
        pass

    # 7. 写入M3U文件
    if os.path.exists(OUT_M3U):
        os.remove(OUT_M3U)
    
    with open(OUT_M3U, "w", encoding="utf-8") as f:
        f.write('#EXTM3U x-tvg-url="https://example.com/epg.xml.gz"\n')
        # 按分类顺序写入
        for gname in [g["name"] for g in CATEGORIES] + ["其他频道"]:
            for name, url in bucket[gname]:
                f.write(f'#EXTINF:-1 group-title="{gname}",{name}\n{url}\n')

    # 8. 写入日志
    elapsed = time.time() - start_time
    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 完成更新 | 总频道数: {len(best_list)} | 本地源: {local_used} | 网络源: {network_used} | 耗时: {elapsed:.2f}s\n"
    with open(LOG_TXT, "a", encoding="utf-8") as f:
        f.write(log_msg)
    
    print(log_msg + "🎉 本地源绝对优先完成！")

if __name__ == "__main__":
    # 关闭requests的SSL警告
    import warnings
    warnings.filterwarnings("ignore")
    main()
