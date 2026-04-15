import os
import re
import requests
import random

# ====================== 配置区（全自动，无需修改）======================
# 文件路径
PRIVATE = "./private.m3u"
MIGU_SRC = "./migu.m3u"
OUTPUT_MAIN = "./output.m3u"
OUTPUT_4K8K = "./output_4k8k.m3u"

# 阿克苏电信固定IP段（兜底）
AKESU_FIXED_CIDR = [
    "110.157.192.0/22", "110.157.196.0/22", "110.157.200.0/21",
    "110.156.213.0/24", "110.156.223.0/24", "110.156.227.0/24",
    "36.109.231.0/24"
]

# 电信常用udpxy组播转发端口
UDPXY_PORTS = ["4022", "5140", "5146", "6666", "8080", "8000", "8888"]

# 🔴 核心：黑名单（过滤1080P/高码/4K8K/移动联通，只留720P及以下）
FILTER_KEYWORDS = {
    "1080P", "1080", "1920", "FHD", "全高清",
    "4K", "2160", "8K", "4k", "2160p", "8k",
    "超高码率", "高码", "60fps", "HDR", "杜比",
    "移动", "CMCC", "移动线路", "联通", "CUCC",
    "udp://", ":8080", ":8081", ":8090", ":9000",
    "超清增强", "极致", "蓝光"
}

# 4K/8K专区标记（自动分离）
UHD_KEYWORDS = {
    "4K", "4k", "2160", "2160p",
    "8K", "8k", "超高清", "UHD"
}

# 白名单：优先保留720P/标清/电信源
TELECOM_KEYS = {
    "电信", "CTCC", "天翼", "itv", "iptv",
    "migu", "720P", "540P", "标清", "高清", "SD"
}

# ====================== 核心功能区（全自动）======================
# 1. 自动抓取最新阿克苏电信udpxy服务器
def fetch_akesu_udpxy():
    servers = []
    try:
        url = "https://ispip.clang.cn/chinatelecom_cidr.html"
        r = requests.get(url, timeout=10)
        ips = re.findall(r'(\d+\.\d+\.\d+\.\d+)', r.text)
        for ip in ips:
            if ip.startswith(("110.157","110.156","36.109")):
                for port in UDPXY_PORTS:
                    servers.append(f"http://{ip}:{port}")
        servers += [f"http://{ip}:{p}" for ip in ["110.157.192.1","36.109.231.253"] for p in UDPXY_PORTS]
    except Exception as e:
        print(f"⚠️ 自动抓取阿克苏IP失败，使用固定兜底IP: {e}")
        servers = [f"http://{ip}:{p}" for ip in ["110.157.192.1","36.109.231.253"] for p in UDPXY_PORTS]
    return list(dict.fromkeys(servers))[:20]

AKESU_SERVERS = fetch_akesu_udpxy()
print(f"📍 已获取阿克苏本地udpxy服务器：{len(AKESU_SERVERS)}个")

# 2. 核心：把任意源转为阿克苏本地线路（秒播不卡顿）
def to_akesu_local(url):
    m = re.search(r'(\d+\.\d+\.\d+\.\d+:\d+)', url)
    if not m:
        return url
    multi_addr = m.group(1)
    server = random.choice(AKESU_SERVERS) if AKESU_SERVERS else "http://110.157.192.1:4022"
    return f"{server}/udp/{multi_addr}"

# 3. 读取M3U文件（容错处理）
def read_m3u(path):
    if not os.path.exists(path):
        print(f"⚠️ 未找到文件: {path}，跳过")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#EXTM3U")]

# 4. 分离4K8K和普通频道
def split_uhd_and_normal(lines):
    normal = []
    uhd = []
    i = 0
    total = len(lines)
    while i < total:
        line = lines[i]
        if line.startswith("#EXTINF"):
            if i + 1 >= total:
                normal.append(line)
                i += 1
                continue
            url = lines[i+1]
            new_url = to_akesu_local(url)
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

# 5. 过滤普通列表：只留720P/标清/电信，过滤1080P/高码/移动联通
def filter_720p_telecom(lines):
    result = []
    skip_next = False
    for line in lines:
        if skip_next:
            skip_next = False
            continue
        # 命中黑名单（1080P/高码等），直接跳过
        if any(k in line for k in FILTER_KEYWORDS):
            skip_next = True
            continue
        # 链接全部保留，白名单/普通频道不删除
        if line.startswith("http") or any(t in line for t in TELECOM_KEYS):
            result.append(line)
        else:
            result.append(line)
    return result

# 6. 链接去重
def deduplicate(lines):
    seen_url = set()
    final = []
    for line in lines:
        if line.startswith("http"):
            if line in seen_url:
                continue
            seen_url.add(line)
        final.append(line)
    return final

# 7. 保存M3U文件
def save_m3u(path, content):
    final = ["#EXTM3U"] + content
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(final))

# ====================== 主流程（全自动）======================
if __name__ == "__main__":
    print("🚀 开始执行直播源自动更新（阿克苏720P稳定版）")
    private = read_m3u(PRIVATE)
    migu = read_m3u(MIGU_SRC)
    all_lines = private + migu

    raw_normal, raw_uhd = split_uhd_and_normal(all_lines)
    # 🔴 核心：只保留720P及以下，过滤1080P
    clean_normal = filter_720p_telecom(raw_normal)
    clean_normal = deduplicate(clean_normal)
    clean_uhd = deduplicate(raw_uhd)

    if len(clean_normal) < 15:
        print("⚠️ 过滤后普通源过少，回退为原始合并模式")
        clean_normal = deduplicate(raw_normal)

    save_m3u(OUTPUT_MAIN, clean_normal)
    save_m3u(OUTPUT_4K8K, clean_uhd)

    print(f"✅ 更新完成！")
    print(f"📺 普通电信720P列表：{len(clean_normal)}个频道（阿克苏本地IP，秒播不卡）")
    print(f"🎬 4K/8K独立专区：{len(clean_uhd)}个频道")
    print(f"📍 已过滤1080P失败源，仅保留720P稳定源")
