#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直播源处理脚本
功能：合并本地源、转换为阿克苏代理、去重、分类、失效检测、输出
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

# 阿克苏代理服务器池
AKESU_SERVERS = [
    "http://110.157.192.1:4022",
    "http://110.157.192.1:5140",
    "http://36.109.231.253:5146",
    "http://110.156.223.1:6666"
]

# 高清关键词（只保留明确表示分辨率或画质的词）
FILTER_KEYWORDS = {"1080", "1080P", "FHD", "4K", "8K", "2160", "UHD", "超高清", "HD", "高清"}

# 4K/8K 专属关键词
UHD_KEYWORDS = {"4K", "8K", "2160", "UHD", "超高清"}

# 网络备用源（当本地频道数不足时启用）
FALLBACK_URLS = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u",
    "https://mirror.ghproxy.com/https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/global.m3u"
]

# ==================== 阿克苏线路转换 ====================
def to_akesu_udp(url):
    """
    将普通流地址转换为阿克苏 UDP 代理格式
    支持从 http://ip:port/xxx 或 rtp://ip:port 等格式中提取 IP:端口
    """
    # 匹配 IPv4:端口 格式（兼容 @ 分隔符）
    match = re.search(r'(\d+\.\d+\.\d+\.\d+)[:@](\d+)', url)
    if match:
        ip = match.group(1)
        port = match.group(2)
        addr = f"{ip}:{port}"
        proxy = random.choice(AKESU_SERVERS)
        return f"{proxy}/udp/{addr}"
    # 如果已经是阿克苏格式，直接返回
    if any(server in url for server in AKESU_SERVERS):
        return url
    # 无法提取则返回原地址（后续检测可能会失败）
    return url

# ==================== 读取本地源 ====================
def read_m3u(path):
    """读取 M3U 文件，返回有效的 EXTINF 和 URL 行对"""
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
    """从网络源抓取直播源"""
    all_lines = []
    for u in FALLBACK_URLS:
        try:
            r = requests.get(u, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            r.encoding = "utf-8"
            lines = r.text.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith("#EXTINF") and i + 1 < len(lines):
                    url_line = lines[i + 1].strip()
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
    """
    根据频道名智能添加 group-title 属性
    输入示例：#EXTINF:-1 tvg-id="CCTV1" tvg-name="CCTV1",CCTV-1 综合
    输出示例：#EXTINF:-1 group-title="央视频道",CCTV-1 综合
    """
    # 提取频道名称（最后一个逗号后的内容）
    parts = inf_line.rsplit(',', 1)
    name = parts[-1].strip() if len(parts) > 1 else inf_line.strip()

    # 判断分组
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

    # 返回标准的 EXTINF 行（移除原有 tvg 属性，简化输出）
    return f'#EXTINF:-1 group-title="{group}",{name}'

# ==================== 失效源检测 ====================
def is_url_alive(url):
    """检测流地址是否可用（使用 GET 请求获取少量数据验证）"""
    if not url.startswith("http"):
        return True  # 组播/本地地址跳过检测
    try:
        # 只请求前 2KB 数据，避免长时间下载
        r = requests.get(url, stream=True, timeout=5, headers={"User-Agent": "VLC/3.0"})
        if r.status_code < 500:
            chunk = next(r.iter_content(2048), None)
            return chunk is not None
    except:
        pass
    return False

# ==================== 去重 + 过滤高清 + 剔除失效 ====================
def process_lines(lines):
    """处理原始行对，返回清洗后的列表"""
    res = []
    seen_urls = set()
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF") and i + 1 < len(lines):
            inf = lines[i]
            raw_url = lines[i + 1]
            i += 2

            # 转换为阿克苏代理地址
            url = to_akesu_udp(raw_url)

            # 去重
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # 高清过滤
            if not any(kw in inf for kw in FILTER_KEYWORDS):
                continue

            # 失效检测
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
    """将 4K/8K 频道分离出来"""
    normal, uhd = [], []
    i = 0
    while i < len(lines):
        inf = lines[i]
        url = lines[i + 1]
        i += 2
        if any(kw in inf for kw in UHD_KEYWORDS):
            # 修改分组名为 4K8K 专属
            uhd.append(re.sub(r'group-title="[^"]*"', 'group-title="4K8K专属专区"', inf))
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
    print("=" * 60)
    print("📡 开始处理直播源...")
    print("=" * 60)

    # 1. 读取本地源
    private = read_m3u(PRIVATE)
    migu = read_m3u(MIGU_SRC)
    local = read_m3u(LOCAL_IPTV)

    all_lines = private + migu + local
    print(f"📁 本地源共计 {len(all_lines)//2} 个频道")

    # 2. 若本地源过少，补充网络源
    if len(all_lines) // 2 < 30:
        print("⚠️ 本地频道不足，正在抓取网络备用源...")
        fallback = fetch_fallback()
        all_lines.extend(fallback)
        print(f"🌐 补充后共 {len(all_lines)//2} 个频道")

    # 3. 核心处理
    cleaned = process_lines(all_lines)
    normal, uhd = split_uhd(cleaned)

    # 4. 输出文件
    save_m3u(OUTPUT_MAIN, normal)
    save_m3u(OUTPUT_4K8K, uhd)

    print("=" * 60)
    print("✅ 处理完成！")
    print(f"📺 有效普通频道：{len(normal)//2} 个")
    print(f"📺 有效4K/8K频道：{len(uhd)//2} 个")
    print(f"📂 输出文件：{OUTPUT_MAIN}、{OUTPUT_4K8K}")
    print("=" * 60)