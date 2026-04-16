import os
import re
import random
import requests

# ==================== 核心配置 ====================
PRIVATE = "./private.m3u"
MIGU_SRC = "./migu.m3u"
LOCAL_IPTV = "./iptv.m3u"
OUTPUT_MAIN = "./iptv.m3u"
OUTPUT_4K8K = "./4K8K专属.m3u"

# 阿克苏服务器
AKESU_SERVERS = [
    "http://110.157.192.1:4022",
    "http://110.157.192.1:5140",
    "http://36.109.231.253:5146",
    "http://110.156.223.1:6666"
]

FILTER_KEYWORDS = {"1080", "1080P", "FHD", "4K", "8K", "2160", "UHD", "超高清", "移动", "CMCC", "联通", "CUCC"}
UHD_KEYWORDS = {"4K", "8K", "2160", "UHD", "超高清"}

# 网络备用源
FALLBACK_URLS = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u",
    "https://raw.githubusercontent.com/joevitor23/IPTV/main/China.m3u"
]

# ==================== 阿克苏线路转换 ====================
def to_akesu_udp(url):
    try:
        match = re.search(r'(\d+\.\d+\.\d+\.\d+[:@]\d+)', url)
        if match:
            addr = match.group(1).replace('@', ':')
            return f"{random.choice(AKESU_SERVERS)}/udp/{addr}"
    except:
        pass
    return url

# ==================== 读取本地源 ====================
def read_m3u(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip() and not l.startswith("#EXTM3U")]
    except:
        return []

# ==================== 抓取网络备用源 ====================
def fetch_fallback():
    lines = []
    for u in FALLBACK_URLS:
        try:
            r = requests.get(u, timeout=8)
            r.encoding = "utf-8"
            for line in r.text.splitlines():
                line = line.strip()
                if line and not line.startswith("#EXTM3U"):
                    lines.append(line)
        except:
            continue
    return lines

# ==================== 频道分类 ====================
def set_group(inf):
    inf = re.sub(r'group-title="[^"]+"', "", inf).strip()
    if re.search(r'CCTV|CGTN|CETV|央视|中国教育', inf, re.I):
        return re.sub(r',(.+)$', r' group-title="央视频道",\1', inf)
    elif re.search(r'卫视', inf):
        return re.sub(r',(.+)$', r' group-title="卫视频道",\1', inf)
    elif re.search(r'电影|影视|剧场|CHC|影院|轮播|大片', inf, re.I):
        return re.sub(r',(.+)$', r' group-title="影视频道",\1', inf)
    elif re.search(r'台|都市|经济|生活|公共|少儿|新闻|文旅|影视', inf):
        return re.sub(r',(.+)$', r' group-title="地方频道",\1', inf)
    else:
        return re.sub(r',(.+)$', r' group-title="其他频道",\1', inf)

# ==================== 失效源检测（直接删除无效源） ====================
def is_url_alive(url):
    try:
        if url.startswith("http"):
            r = requests.head(url, timeout=4, allow_redirects=True)
            return r.status_code < 400
        return True
    except:
        return False

# ==================== 去重 + 过滤高清 + 剔除失效 ====================
def process_lines(lines):
    res, seen = [], set()
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF") and i+1 < len(lines):
            inf, url = lines[i], to_akesu_udp(lines[i+1])
            i += 2
            if url in seen:
                continue
            seen.add(url)
            # 过滤高清
            if not any(k in inf for k in FILTER_KEYWORDS):
                continue
            # 检测失效
            if not is_url_alive(url):
                continue
            # 分类
            inf = set_group(inf)
            res.append(inf)
            res.append(url)
        else:
            i += 1
    return res

# ==================== 拆分普通/4K ====================
def split_uhd(lines):
    normal, uhd = [], []
    i = 0
    while i < len(lines):
        inf, url = lines[i], lines[i+1]
        i += 2
        if any(k in inf for k in UHD_KEYWORDS):
            uhd.append(re.sub(r'group-title="[^"]+"', 'group-title="4K8K专属专区"', inf))
            uhd.append(url)
        else:
            normal.append(inf)
            normal.append(url)
    return normal, uhd

# ==================== 保存 ====================
def save_m3u(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n" + "\n".join(lines))

# ==================== 主程序 ====================
if __name__ == "__main__":
    # 优先本地
    private = read_m3u(PRIVATE)
    migu = read_m3u(MIGU_SRC)
    local = read_m3u(LOCAL_IPTV)
    all_lines = private + migu + local

    # 不足则补网络源
    if len(all_lines) < 20:
        all_lines += fetch_fallback()

    # 处理：去重+高清+失效检测+分类+阿克苏线路
    cleaned = process_lines(all_lines)
    normal, uhd = split_uhd(cleaned)

    # 覆盖输出
    save_m3u(OUTPUT_MAIN, normal)
    save_m3u(OUTPUT_4K8K, uhd)

    print("="*60)
    print("✅ 全部功能已执行完成！")
    print(f"📺 有效普通频道：{len(normal)//2} 个")
    print(f"📺 有效4K/8K频道：{len(uhd)//2} 个")
    print("🔍 已自动：优先本地 + 失效删除 + 阿克苏优化 + 精准分类")
    print("📂 输出文件：iptv.m3u、4K8K专属.m3u")
    print("="*60)
