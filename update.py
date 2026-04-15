import os
import re
import requests
import random

# 文件配置
PRIVATE = "./private.m3u"
MIGU_SRC = "./migu.m3u"
OUTPUT_MAIN = "./output.m3u"
OUTPUT_4K8K = "./output_4k8k.m3u"

# 阿克苏电信固定IP段（兜底）
AKESU_CIDR = [
    "110.157.192.0/22", "110.157.196.0/22", "110.157.200.0/21",
    "110.156.213.0/24", "110.156.223.0/24", "110.156.227.0/24",
    "36.109.231.0/24"
]

# 电信常用udpxy端口（组播转发）
UDPXY_PORTS = ["4022", "5140", "5146", "6666", "8080", "8000", "8888"]

# 过滤规则
FILTER = {"4K","8K","2160","高码","60fps","HDR","杜比","移动","CMCC","联通","CUCC"}
UHD = {"4K","8K","2160","UHD","超高清"}
TELECOM = {"电信","CTCC","天翼","itv","iptv","migu","1080P","720P"}

# ------------------------------
# 1. 自动抓取最新阿克苏udpxy服务器
# ------------------------------
def fetch_akesu_udpxy():
    servers = []
    try:
        # 从公开IP库抓取阿克苏电信IP
        url = "https://ispip.clang.cn/chinatelecom_cidr.html"
        r = requests.get(url, timeout=10)
        ips = re.findall(r'(\d+\.\d+\.\d+\.\d+)', r.text)
        # 筛选阿克苏段
        for ip in ips:
            if ip.startswith(("110.157","110.156","36.109")):
                for port in UDPXY_PORTS:
                    servers.append(f"http://{ip}:{port}")
        # 兜底固定服务器
        servers += [f"http://{ip}:{p}" for ip in ["110.157.192.1","36.109.231.253"] for p in UDPXY_PORTS]
    except:
        pass
    # 去重+取前20
    return list(dict.fromkeys(servers))[:20]

AKESU_SERVERS = fetch_akesu_udpxy()
print(f"📍 已获取阿克苏udpxy服务器：{len(AKESU_SERVERS)}个")

# ------------------------------
# 2. 把任意源转为阿克苏线路（核心！）
# ------------------------------
def to_akesu(url):
    # 提取组播地址（239.x.x.x:端口）
    m = re.search(r'(\d+\.\d+\.\d+\.\d+:\d+)', url)
    if not m:
        return url
    multi = m.group(1)
    # 随机选阿克苏服务器
    server = random.choice(AKESU_SERVERS) if AKESU_SERVERS else "http://110.157.192.1:4022"
    return f"{server}/udp/{multi}"

# ------------------------------
# 3. 读取、拆分、过滤、去重
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
            new_url = to_akesu(url)
            if any(k in line for k in UHD):
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

def filter_list(lines):
    res, skip = [], False
    for line in lines:
        if skip: skip=False; continue
        if any(k in line for k in FILTER):
            skip=True
            continue
        if line.startswith("http") or any(t in line for t in TELECOM):
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

    print(f"✅ 生成完成（全阿克苏线路）")
    print(f"📺 普通({len(normal)}) | 🎬 4K8K({len(uhd)})")
