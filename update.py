#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直播源处理脚本 - 保留最大化版本
"""

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

AKESU_SERVERS = [
    "http://110.157.192.1:4022",
    "http://110.157.192.1:5140",
    "http://36.109.231.253:5146",
    "http://110.156.223.1:6666"
]

# 高清关键词 —— 改为空集合，不再过滤画质
FILTER_KEYWORDS = set()

# 4K/8K 专属关键词
UHD_KEYWORDS = {"4K", "8K", "2160", "UHD", "超高清"}

# 失效检测开关 —— 设为 False 跳过网络检测（避免超时误杀）
ENABLE_URL_CHECK = False

FALLBACK_URLS = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u",
    "https://mirror.ghproxy.com/https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/global.m3u"
]

# ==================== 阿克苏线路转换 ====================
def to_akesu_udp(url):
    # 如果已是阿克苏格式，直接返回
    if any(server in url for server in AKESU_SERVERS):
        return url
    # 提取 IP:端口
    match = re.search(r'(\d+\.\d+\.\d+\.\d+)[:@](\d+)', url)
    if match:
        ip = match.group(1)
        port = match.group(2)
        addr = f"{ip}:{port}"
        proxy = random.choice(AKESU_SERVERS)
        return f"{proxy}/udp/{addr}"
    # 无法提取则原样返回（后续检测可能失败，但先保留）
    return url

# ==================== 读取本地源 ====================
def read_m3u(path):
    if not os.path.exists(path):
        return []
    lines = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().splitlines()
        i = 0
        while i < len(content):
            line = content[i].strip()
            if line.startswith("#EXTINF") and i + 1 < len(content):
                url_line = content[i + 1].strip()
                if url_line and not url_line.startswith("#"):
                    lines.append(line)
                    lines.append(url_line)
                i += 2
            else:
                i += 1
    except Exception as e:
        print(f"读取 {path} 失败: {e}")
    return lines

# ==================== 抓取网络备用源 ====================
def fetch_fallback():
    all_lines = []
    for u in FALLBACK_URLS:
        try:
            r = requests.get(u, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            r.encoding = "utf-8"
            raw = r.text.splitlines()
            i = 0
            while i < len(raw):
                line = raw[i].strip()
                if line.startswith("#EXTINF") and i + 1 < len(raw):
                    url_line = raw[i + 1].strip()
                    if url_line and not url_line.startswith("#"):
                        all_lines.append(line)
                        all_lines.append(url_line)
                    i += 2
                else:
                    i += 1
        except Exception as e:
            print(f"抓取备用源失败 {u}: {e}")
    return all_lines

# ==================== 频道分类 ====================
def set_group(inf_line):
    parts = inf_line.rsplit(',', 1)
    name = parts[-1].strip() if len(parts) > 1 else inf_line.strip()
    if re.search(r'CCTV|CGTN|CETV|央视|中国教育', name, re.I):
        group = "央视频道"
    elif re.search(r'卫视', name):
        group = "卫视频道"
    elif re.search(r'电影|影视|剧场|CHC|影院|轮播|大片|好莱坞', name, re.I):
        group = "影视频道"
    elif re.search(r'台|都市|经济|生活|公共|少儿|新闻|文旅|综艺|纪实', name):
        group = "地方频道"
    else:
        group = "其他频道"
    return f'#EXTINF:-1 group-title="{group}",{name}'

# ==================== 失效源检测（已禁用） ====================
def is_url_alive(url):
    if not ENABLE_URL_CHECK:
        return True
    if not url.startswith("http"):
        return True
    try:
        r = requests.get(url, stream=True, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        return r.status_code < 400
    except:
        return False

# ==================== 去重 + 分类 ====================
def process_lines(lines):
    res = []
    seen_urls = set()
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF") and i + 1 < len(lines):
            inf = lines[i]
            raw_url = lines[i + 1]
            i += 2

            url = to_akesu_udp(raw_url)
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # 画质过滤（当前为空，全部通过）
            if FILTER_KEYWORDS and not any(kw in inf for kw in FILTER_KEYWORDS):
                continue

            # 失效检测（已禁用）
            if not is_url_alive(url):
                continue

            inf = set_group(inf)
            res.append(inf)
            res.append(url)
        else:
            i += 1
    return res

# ==================== 拆分4K ====================
def split_uhd(lines):
    normal, uhd = [], []
    i = 0
    while i < len(lines):
        inf = lines[i]
        url = lines[i + 1]
        i += 2
        if any(kw in inf for kw in UHD_KEYWORDS):
            uhd.append(re.sub(r'group-title="[^"]*"', 'group-title="4K8K专属专区"', inf))
            uhd.append(url)
        else:
            normal.append(inf)
            normal.append(url)
    return normal, uhd

def save_m3u(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n" + "\n".join(lines))

if __name__ == "__main__":
    print("=" * 60)
    print("📡 开始处理直播源...")

    private = read_m3u(PRIVATE)
    migu = read_m3u(MIGU_SRC)
    local = read_m3u(LOCAL_IPTV)
    all_lines = private + migu + local
    print(f"📁 本地源共计 {len(all_lines)//2} 个频道")

    if len(all_lines) // 2 < 20:
        print("⚠️ 本地频道较少，抓取网络备用源...")
        all_lines.extend(fetch_fallback())

    cleaned = process_lines(all_lines)
    normal, uhd = split_uhd(cleaned)

    save_m3u(OUTPUT_MAIN, normal)
    save_m3u(OUTPUT_4K8K, uhd)

    print("=" * 60)
    print(f"✅ 有效普通频道：{len(normal)//2} 个")
    print(f"✅ 有效4K/8K频道：{len(uhd)//2} 个")
    print(f"📂 输出：{OUTPUT_MAIN}、{OUTPUT_4K8K}")
    print("=" * 60)