import os
import re
import requests
from ipaddress import ip_address, ip_network

# 文件配置
PRIVATE = "./private.m3u"
MIGU_SRC = "./migu.m3u"
OUTPUT_MAIN = "./output.m3u"
OUTPUT_4K8K = "./output_4k8k.m3u"

# 阿克苏电信固定IP段（兜底）
AKESU_FIXED_CIDR = [
    "110.157.192.0/22", "110.157.196.0/22", "110.157.200.0/21",
    "110.156.213.0/24", "110.156.223.0/24", "110.156.227.0/24"
]

# 常用电信代理端口（组播转发常用）
AKESU_PORTS = ["8080", "6666", "4022", "5140", "5146", "8000"]

# 过滤规则
FILTER_KEYWORDS = {"4K","8K","2160","高码","60fps","HDR","杜比","移动","CMCC","联通","CUCC","udp://"}
UHD_KEYWORDS = {"4K","8K","2160","UHD","超高清"}
TELECOM_KEYS = {"电信","CTCC","天翼","itv","iptv","migu","1080P","720P"}

# ------------------------------
# 1. 自动获取最新阿克苏电信IP
# ------------------------------
def fetch_latest_akesu_cidr():
    try:
        url = "https://ispip.clang.cn/chinatelecom_cidr.html"
        r = requests.get(url, timeout=10)
        cidrs = re.findall(r'(\d+\.\d+\.\d+\.\d+/\d+)', r.text)
        akesu = []
        for c in cidrs:
            net = ip_network(c, strict=False)
            if any(net.overlaps(ip_network(fc)) for fc in AKESU_FIXED_CIDR):
                akesu.append(c)
        return list(set(akesu + AKESU_FIXED_CIDR))[:8]
    except:
        print("⚠️ 自动获取失败，使用固定阿克苏段")
        return AKESU_FIXED_CIDR[:8]

AKESU_NETS = [ip_network(c) for c in fetch_latest_akesu_cidr()]

# ------------------------------
# 2. 判断IP是否阿克苏电信
# ------------------------------
def is_akesu_ip(ip_str):
    try:
        ip = ip_address(ip_str)
        return any(ip in net for net in AKESU_NETS)
    except:
        return False

# ------------------------------
# 3. 自动补充阿克苏IP+端口
# ------------------------------
def rewrite_to_akesu(url):
    match = re.match(r'https?://([^:/]+):?(\d+)?(/.*)?', url)
    if not match:
        return url
    host, port, path = match.groups()
    if is_akesu_ip(host):
        return url
    # 随机选阿克苏IP+端口
    import random
    new_ip = random.choice([str net.network_address for net in AKESU_NETS])
    new_port = random.choice(AKESU_PORTS)
    new_path = path if path else "/udp/239.3.1.1:5140"
    return f"http://{new_ip}:{new_port}{new_path}"

# ------------------------------
# 4. 读取、拆分、过滤、去重
# ------------------------------
def read_m3u(path):
    if not os.path.exists(path):
        print(f"⚠️ 未找到: {path}")
        return []
    with open(path,"r",encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]

def split_uhd_normal(lines):
    normal, uhd = [], []
    i=0; n=len(lines)
    while i < n:
        line = lines[i]
        if line.startswith("#EXTINF") and i+1 < n:
            url = lines[i+1]
            if any(k in line for k in UHD_KEYWORDS):
                uhd.append(line)
                uhd.append(rewrite_to_akesu(url))
            else:
                normal.append(line)
                normal.append(rewrite_to_akesu(url))
            i += 2
        else:
            normal.append(line)
            i += 1
    return normal, uhd

def filter_list(lines):
    res, skip = [], False
    for line in lines:
        if skip: skip=False; continue
        if any(k in line for k in FILTER_KEYWORDS):
            skip=True
            continue
        if line.startswith("http") or any(t in line for t in TELECOM_KEYS):
            res.append(line)
        else:
            res.append(line)
    return res

def deduplicate(lines):
    seen=set(); out=[]
    for line in lines:
        if line.startswith("http"):
            if line in seen: continue
            seen.add(line)
        out.append(line)
    return out

def save(path, lines):
    with open(path,"w",encoding="utf-8") as f:
        f.write("#EXTM3U\n"+"\n".join(lines))

# ------------------------------
# 主流程
# ------------------------------
if __name__ == "__main__":
    private = read_m3u(PRIVATE)
    migu = read_m3u(MIGU_SRC)
    all_lines = private + migu

    normal, uhd = split_uhd_normal(all_lines)
    normal = filter_list(normal)
    normal = deduplicate(normal)
    uhd = deduplicate(uhd)

    if len(normal) < 15:
        print("⚠️ 普通源过少，恢复原始")
        normal = deduplicate(private + migu)

    save(OUTPUT_MAIN, normal)
    save(OUTPUT_4K8K, uhd)

    print(f"✅ 生成完成")
    print(f"📺 普通({len(normal)}) | 🎬 4K8K({len(uhd)})")
    print(f"📍 已强制优先阿克苏电信IP")
