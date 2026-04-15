import os
import re
import random

# ==================== 配置 ====================
PRIVATE = "./private.m3u"
MIGU_SRC = "./migu.m3u"
OUTPUT_MAIN = "./output.m3u"
OUTPUT_4K8K = "./output_4k8k.m3u"

# 阿克苏本地线路（保证稳定秒播）
AKESU_SERVERS = [
    "http://110.157.192.1:4022",
    "http://110.157.192.1:5140",
    "http://36.109.231.253:5146",
    "http://110.156.223.1:6666"
]

# 只过滤真正卡的：1080P+/4K/8K/移动/联通，其他一律保留！
FILTER_KEYWORDS = {
    "1080", "1080P", "FHD",
    "4K", "8K", "2160", "UHD", "超高清",
    "移动", "CMCC", "联通", "CUCC"
}

# 4K/8K 单独抽出来
UHD_KEYWORDS = {"4K", "8K", "2160", "UHD", "超高清"}

# ==================== 核心功能 ====================
# 转为阿克苏本地线路，保证稳定
def to_akesu(url):
    match = re.search(r'(\d+\.\d+\.\d+\.\d+:\d+)', url)
    if not match:
        return url
    server = random.choice(AKESU_SERVERS)
    return f"{server}/udp/{match.group(1)}"

# 读取m3u
def read_m3u(path):
    if not os.path.exists(path):
        print(f"⚠️ 未找到 {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

# 分离 4K8K 和普通频道
def split_uhd_normal(lines):
    normal = []
    uhd = []
    i = 0
    total = len(lines)
    while i < total:
        line = lines[i]
        if line.startswith("#EXTINF") and i + 1 < total:
            url = lines[i+1]
            new_url = to_akesu(url)
            if any(k in line for k in UHD_KEYWORDS):
                uhd.append(line)
                uhd.append(new_url)
            else:
                normal.append(line)
                normal.append(new_url)
            i += 2
        else:
            normal.append(line)
            i += 1
    return normal, uhd

# 轻柔过滤：只删1080+/移动/联通，不删影视/轮播/港澳台
def gentle_filter(lines):
    out = []
    skip_next = False
    for line in lines:
        if skip_next:
            skip_next = False
            continue
        # 只删黑名单内容
        if any(k in line for k in FILTER_KEYWORDS):
            skip_next = True
            continue
        out.append(line)
    return out

# 去重
def deduplicate(lines):
    seen_url = set()
    out = []
    for line in lines:
        if line.startswith("http"):
            if line in seen_url:
                continue
            seen_url.add(line)
        out.append(line)
    return out

# 自动分组（不覆盖原有分组）
def auto_group(lines, default_group):
    res = []
    for line in lines:
        if line.startswith("#EXTINF") and "group-title=" not in line:
            line = re.sub(r',(.+)$', f' group-title="{default_group}",\\1', line)
        res.append(line)
    return res

# 保存文件
def save_m3u(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n" + "\n".join(lines))

# ==================== 主程序 ====================
if __name__ == "__main__":
    private = read_m3u(PRIVATE)
    migu = read_m3u(MIGU_SRC)
    all_lines = private + migu

    # 分离4K8K
    normal_lines, uhd_lines = split_uhd_normal(all_lines)

    # 轻柔过滤，不删影视/轮播/港澳台
    normal_lines = gentle_filter(normal_lines)
    normal_lines = deduplicate(normal_lines)
    uhd_lines = deduplicate(uhd_lines)

    # 自动分组
    normal_lines = auto_group(normal_lines, "电信稳定·720P")
    uhd_lines = auto_group(uhd_lines, "4K8K专属专区")

    # 兜底
    if len(normal_lines) < 10:
        normal_lines = deduplicate(private + migu)

    save_m3u(OUTPUT_MAIN, normal_lines)
    save_m3u(OUTPUT_4K8K, uhd_lines)

    print("✅ 最终稳定版生成完成")
    print(f"📺 普通频道(含影视/轮播/港澳台)：{len(normal_lines)//2} 个")
    print(f"🎬 4K8K专区：{len(uhd_lines)//2} 个")
    print("📍 全部走阿克苏本地IP，不再乱删频道")
