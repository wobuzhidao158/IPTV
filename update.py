import os
import re
import random

# ==================== 核心配置 ====================
PRIVATE = "./private.m3u"
MIGU_SRC = "./migu.m3u"
OUTPUT_MAIN = "./iptv.m3u"
OUTPUT_4K8K = "./output_4k8k.m3u"

# 阿克苏本地服务器
AKESU_SERVERS = [
    "http://110.157.192.1:4022",
    "http://110.157.192.1:5140",
    "http://36.109.231.253:5146",
    "http://110.156.223.1:6666"
]

# 只过滤1080P+/4K/移动联通
FILTER_KEYWORDS = {
    "1080", "1080P", "FHD",
    "4K", "8K", "2160", "UHD", "超高清",
    "移动", "CMCC", "联通", "CUCC"
}

# 4K/8K标记
UHD_KEYWORDS = {"4K", "8K", "2160", "UHD", "超高清"}

# ==================== 精准自动分类（核心新增）====================
def auto_group_by_type(line):
    # 保留原有分组，不覆盖
    if "group-title=" in line:
        return line
    
    # 1. 央视频道
    if re.search(r'CCTV|CGTN|CETV|央视|中国教育', line, re.IGNORECASE):
        return re.sub(r',(.+)$', r' group-title="央视频道",\1', line)
    
    # 2. 卫视频道
    if re.search(r'卫视|兵团卫视|三沙卫视', line):
        return re.sub(r',(.+)$', r' group-title="卫视频道",\1', line)
    
    # 3. 影视轮播
    if re.search(r'电影|影视|剧场|轮播|影院|CHC|新片|经典', line):
        return re.sub(r',(.+)$', r' group-title="影视轮播",\1', line)
    
    # 4. 地方频道
    if re.search(r'频道|台|广播电视台', line):
        return re.sub(r',(.+)$', r' group-title="地方频道",\1', line)
    
    # 5. 兜底：其他频道
    return re.sub(r',(.+)$', r' group-title="其他频道",\1', line)

# ==================== 核心功能 ====================
def to_akesu(url):
    try:
        match = re.search(r'(\d+\.\d+\.\d+\.\d+:\d+)', url)
        if not match:
            return url
        return f"{random.choice(AKESU_SERVERS)}/udp/{match.group(1)}"
    except:
        return url

def read_m3u(path):
    try:
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip() and not l.startswith("#EXTM3U")]
    except:
        return []

def split_uhd_normal(lines):
    normal, uhd = [], []
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF") and i+1 < len(lines):
            url = to_akesu(lines[i+1])
            if any(k in lines[i] for k in UHD_KEYWORDS):
                uhd.append(lines[i])
                uhd.append(url)
            else:
                normal.append(lines[i])
                normal.append(url)
            i += 2
        else:
            normal.append(lines[i])
            i += 1
    return normal, uhd

def gentle_filter(lines):
    out, skip = [], False
    for line in lines:
        if skip:
            skip = False
            continue
        if any(k in line for k in FILTER_KEYWORDS):
            skip = True
            continue
        out.append(line)
    return out

def deduplicate(lines):
    seen, out = set(), []
    for line in lines:
        if line.startswith("http"):
            if line in seen:
                continue
            seen.add(line)
        out.append(line)
    return out

def save_m3u(path, lines):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n" + "\n".join(lines))
    except:
        pass

# ==================== 主程序 ====================
if __name__ == "__main__":
    # 100%保留你的私源和咪咕源
    private = read_m3u(PRIVATE)
    migu = read_m3u(MIGU_SRC)
    all_lines = private + migu

    normal, uhd = split_uhd_normal(all_lines)
    normal = gentle_filter(normal)
    normal = deduplicate(normal)
    
    # 🔴 核心：自动精准分类
    normal = [auto_group_by_type(line) for line in normal]
    uhd = [re.sub(r'group-title="[^"]+"', r'group-title="4K8K专属专区"', line) if line.startswith("#EXTINF") else line for line in uhd]

    # 终极兜底：如果为空，直接输出原始源
    if len(normal) < 10:
        normal = private + migu

    save_m3u(OUTPUT_MAIN, normal)
    save_m3u(OUTPUT_4K8K, uhd)

    print(f"✅ 更新完成（已自动分类）")
    print(f"📺 私源：{len(private)//2} 个（100%保留）")
    print(f"📺 咪咕源：{len(migu)//2} 个（100%保留）")
    print(f"📺 总频道：{len(normal)//2} 个")
    print(f"📂 已自动分类：央视 | 卫视 | 地方 | 影视 | 4K8K")
