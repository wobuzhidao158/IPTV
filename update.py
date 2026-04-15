import os
import re
import random
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 核心配置 ====================
PRIVATE = "./private.m3u"
MIGU_SRC = "./migu.m3u"
OUTPUT_MAIN = "./output.m3u"
OUTPUT_4K8K = "./output_4k8k.m3u"

# 阿克苏本地服务器（稳定秒播）
AKESU_SERVERS = [
    "http://110.157.192.1:4022",
    "http://110.157.192.1:5140",
    "http://36.109.231.253:5146",
    "http://110.156.223.1:6666"
]

# 只过滤：1080P+/4K/8K/移动/联通，其他全留
FILTER_KEYWORDS = {
    "1080", "1080P", "FHD",
    "4K", "8K", "2160", "UHD", "超高清",
    "移动", "CMCC", "联通", "CUCC"
}

# 4K/8K专区标记
UHD_KEYWORDS = {"4K", "8K", "2160", "UHD", "超高清"}

# 源有效性检测超时（秒）
CHECK_TIMEOUT = 5
# 最大并发检测数
MAX_WORKERS = 20

# ==================== 核心功能 ====================
# 转为阿克苏本地IP
def to_akesu(url):
    match = re.search(r'(\d+\.\d+\.\d+\.\d+:\d+)', url)
    if not match:
        return url
    server = random.choice(AKESU_SERVERS)
    return f"{server}/udp/{match.group(1)}"

# 检测单个源有效性
def check_url_valid(url):
    try:
        response = requests.head(url, timeout=CHECK_TIMEOUT, allow_redirects=True)
        return url if response.status_code < 400 else None
    except:
        return None

# 批量过滤失效源
def filter_valid_urls(lines):
    url_map = {}
    temp_lines = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF") and i+1 < len(lines):
            info = lines[i]
            url = lines[i+1]
            url_map[url] = info
            temp_lines.append(url)
            i += 2
        else:
            temp_lines.append(lines[i])
            i += 1

    valid_urls = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(check_url_valid, url): url for url in temp_lines if url.startswith("http")}
        for future in as_completed(future_to_url):
            res = future.result()
            if res:
                valid_urls.append(res)

    result = []
    for url in valid_urls:
        if url in url_map:
            result.append(url_map[url])
            result.append(url)
    return result

# 自动补新720P源
def fetch_new_720p_sources():
    new_sources = []
    try:
        urls = [
            "https://cdn.jsdelivr.net/gh/iptv-org/iptv@master/streams/cn.m3u",
            "https://ghp.ci/https://raw.githubusercontent.com/kimwang1978/collect-tv-txt/main/merged_output.m3u"
        ]
        for url in urls:
            r = requests.get(url, timeout=10)
            lines = r.text.split("\n")
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith("#EXTINF"):
                    if i+1 >= len(lines):
                        i += 1
                        continue
                    url_line = lines[i+1].strip()
                    if "720" in line or "标清" in line or "电信" in line:
                        if not any(k in line for k in FILTER_KEYWORDS):
                            new_sources.append(line)
                            new_sources.append(url_line)
                    i += 2
                else:
                    i += 1
    except:
        pass
    return new_sources

# 读取m3u
def read_m3u(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#EXTM3U")]

# 分离4K8K和普通频道
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

# 轻柔过滤，不删影视/轮播/港澳台
def gentle_filter(lines):
    out = []
    skip_next = False
    for line in lines:
        if skip_next:
            skip_next = False
            continue
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

    normal_lines, uhd_lines = split_uhd_normal(all_lines)
    normal_lines = gentle_filter(normal_lines)
    normal_lines = filter_valid_urls(normal_lines)
    uhd_lines = filter_valid_urls(uhd_lines)

    if len(normal_lines) < 30:
        new_sources = fetch_new_720p_sources()
        normal_lines.extend(new_sources)
        normal_lines = gentle_filter(normal_lines)
        normal_lines = filter_valid_urls(normal_lines)

    normal_lines = deduplicate(normal_lines)
    normal_lines = auto_group(normal_lines, "电信稳定·720P")
    uhd_lines = deduplicate(uhd_lines)
    uhd_lines = auto_group(uhd_lines, "4K8K专属专区")

    save_m3u(OUTPUT_MAIN, normal_lines)
    save_m3u(OUTPUT_4K8K, uhd_lines)

    print(f"✅ 更新完成！")
    print(f"📺 普通频道：{len(normal_lines)//2} 个有效源")
    print(f"🎬 4K8K专区：{len(uhd_lines)//2} 个有效源")
