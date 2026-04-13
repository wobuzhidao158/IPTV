import requests
import re
import time
from typing import List, Dict

# ====================== 配置区域（请根据你的需求修改） ======================
# 私源列表（优先级最高，排在最前面，重复频道保留私源）
PRIVATE_SOURCES = [
    # "https://你的私源地址1.m3u",
    # "https://你的私源地址2.txt",
]

# 公共源列表（私源之后加载，已自动加入咪咕1080P公开源）
PUBLIC_SOURCES = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u",
    "https://raw.githubusercontent.com/FongMi/TV/main/TV/migu.txt",  # 👈 已自动添加咪咕1080P央卫源
    # 可以添加更多公共源
]

# 4K8K专区关键词（匹配到任意一个就会归类到4K8K专区）
_4K8K_KEYWORDS = ["4K", "8K", "超高清", "4K超清", "8K超清", "UHD", "HDR", "杜比视界"]

# 输出文件名
OUTPUT_M3U = "live.m3u"
OUTPUT_TXT = "live.txt"

# 请求超时时间（秒）
REQUEST_TIMEOUT = 15
# ======================================================================

def download_url(url: str) -> str:
    """下载URL内容，自动处理编码问题"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # 自动检测编码
        if response.encoding.lower() == 'iso-8859-1':
            for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-16']:
                try:
                    return response.content.decode(encoding)
                except UnicodeDecodeError:
                    continue
        return response.text
    except Exception as e:
        print(f"❌ 下载失败 {url}: {str(e)}")
        return ""

def parse_m3u(content: str) -> List[Dict]:
    """解析M3U格式内容，返回频道列表"""
    channels = []
    lines = content.splitlines()
    i = 0
    current_extinf = ""
    
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
            
        if line.startswith('#EXTINF:'):
            current_extinf = line
            # 提取频道名称
            name_match = re.search(r',\s*(.*)$', line)
            name = name_match.group(1).strip() if name_match else "未知频道"
            i += 1
            
            # 找到下一个非空行作为URL
            while i < len(lines):
                url_line = lines[i].strip()
                if url_line and not url_line.startswith('#'):
                    channels.append({
                        "name": name,
                        "url": url_line,
                        "extinf": current_extinf
                    })
                    break
                i += 1
        else:
            i += 1
            
    return channels

def parse_txt(content: str) -> List[Dict]:
    """解析TXT格式内容（频道名,URL），返回频道列表"""
    channels = []
    lines = content.splitlines()
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        parts = line.split(',', 1)
        if len(parts) == 2:
            name = parts[0].strip()
            url = parts[1].strip()
            if url.startswith(('http://', 'https://', 'rtsp://')):
                channels.append({
                    "name": name,
                    "url": url,
                    "extinf": f"#EXTINF:-1,{name}"
                })
                
    return channels

def deduplicate_channels(channels: List[Dict]) -> List[Dict]:
    """根据URL去重，保留先出现的（私源优先）"""
    seen_urls = set()
    unique_channels = []
    
    for channel in channels:
        url = channel["url"].strip()
        if url not in seen_urls:
            seen_urls.add(url)
            unique_channels.append(channel)
            
    return unique_channels

def categorize_channels(channels: List[Dict]) -> tuple[List[Dict], List[Dict]]:
    """分类：普通频道 / 4K8K专区"""
    normal_channels = []
    _4k8k_channels = []
    
    for channel in channels:
        name = channel["name"].upper()
        is_4k8k = any(keyword.upper() in name for keyword in _4K8K_KEYWORDS)
        
        if is_4k8k:
            _4k8k_channels.append(channel)
        else:
            normal_channels.append(channel)
            
    return normal_channels, _4k8k_channels

def generate_m3u(normal_channels: List[Dict], _4k8k_channels: List[Dict]) -> str:
    """生成最终M3U"""
    m3u_content = "#EXTM3U\n\n"
    
    if normal_channels:
        m3u_content += "#EXTGRP:普通频道\n"
        for channel in normal_channels:
            m3u_content += f"{channel['extinf']}\n{channel['url']}\n\n"
    
    if _4k8k_channels:
        m3u_content += "#EXTGRP:4K8K专区\n"
        for channel in _4k8k_channels:
            m3u_content += f"{channel['extinf']}\n{channel['url']}\n\n"
            
    return m3u_content

def generate_txt(normal_channels: List[Dict], _4k8k_channels: List[Dict]) -> str:
    """生成最终TXT"""
    txt_content = ""
    
    if normal_channels:
        txt_content += "# 普通频道\n"
        for channel in normal_channels:
            txt_content += f"{channel['name']},{channel['url']}\n"
    
    if _4k8k_channels:
        txt_content += "\n# 4K8K专区\n"
        for channel in _4k8k_channels:
            txt_content += f"{channel['name']},{channel['url']}\n"
            
    return txt_content

def main():
    print("🚀 开始更新直播源...")
    all_channels = []
    
    # 1. 加载私源
    print("\n📥 加载私源...")
    for source in PRIVATE_SOURCES:
        print(f"  处理: {source}")
        content = download_url(source)
        if content:
            if source.endswith('.m3u'):
                channels = parse_m3u(content)
            elif source.endswith('.txt'):
                channels = parse_txt(content)
            else:
                channels = parse_m3u(content)
                if not channels:
                    channels = parse_txt(content)
            all_channels.extend(channels)
            print(f"  ✅ 加载了 {len(channels)} 个频道")
    
    # 2. 加载公共源（含咪咕1080P源）
    print("\n📥 加载公共源...")
    for source in PUBLIC_SOURCES:
        print(f"  处理: {source}")
        content = download_url(source)
        if content:
            if source.endswith('.m3u'):
                channels = parse_m3u(content)
            elif source.endswith('.txt'):
                channels = parse_txt(content)
            else:
                channels = parse_m3u(content)
                if not channels:
                    channels = parse_txt(content)
            all_channels.extend(channels)
            print(f"  ✅ 加载了 {len(channels)} 个频道")
    
    # 3. 去重
    print(f"\n🧹 去重前总频道数: {len(all_channels)}")
    unique_channels = deduplicate_channels(all_channels)
    print(f"✅ 去重后总频道数: {len(unique_channels)}")
    
    # 4. 分类
    normal_channels, _4k8k_channels = categorize_channels(unique_channels)
    print(f"\n📊 分类结果:")
    print(f"  普通频道: {len(normal_channels)} 个")
    print(f"  4K8K专区: {len(_4k8k_channels)} 个")

    # 5. 生成输出文件
    m3u_content = generate_m3u(normal_channels, _4k8k_channels)
    txt_content = generate_txt(normal_channels, _4k8k_channels)
    
    with open(OUTPUT_M3U, 'w', encoding='utf-8') as f:
        f.write(m3u_content)
    print(f"\n💾 已生成 {OUTPUT_M3U}")
    
    with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
        f.write(txt_content)
    print(f"💾 已生成 {OUTPUT_TXT}")
    
    print("\n🎉 直播源更新完成！")

if __name__ == "__main__":
    main()
