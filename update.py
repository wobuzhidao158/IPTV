# -*- coding: utf-8 -*-
# 只读取本地「直播源.txt」 自动分类+去重+生成M3U 100%稳定版
import os
from datetime import datetime

# 只读取你本地的直播源.txt，不做任何远程拉取，绝对稳定
INPUT_FILE = "直播源.txt"
OUTPUT_FILE = "iptv.m3u"
LOG_FILE = "update_log.txt"

# ====================== 1:1匹配你要的分类 ======================
CATEGORIES = [
    {"name": "央视频道", "icon": "📺", "keywords": ["CCTV", "央视", "cctv", "中央电视台"]},
    {"name": "卫视频道", "icon": "📺", "keywords": ["卫视", "江苏", "浙江", "东方", "湖南", "北京", "山东", "安徽", "湖北", "广东", "深圳", "天津", "重庆", "四川", "河南", "河北", "辽宁", "吉林", "黑龙江"]},
    {"name": "电影频道", "icon": "🎬", "keywords": ["电影", "影院", "院线", "影视", "剧场"]},
    {"name": "儿童频道", "icon": "👦", "keywords": ["少儿", "儿童", "卡通", "动画", "动漫", "宝贝"]},
    {"name": "香港频道", "icon": "🇭🇰", "keywords": ["香港", "TVB", "ViuTV", "香港开电视"]},
    {"name": "澳门频道", "icon": "🇲🇴", "keywords": ["澳门", "澳广视", "澳门莲花"]},
    {"name": "台湾频道", "icon": "🌊", "keywords": ["台湾", "中天", "东森", "纬来", "民视"]},
    {"name": "新加坡", "icon": "🇸🇬", "keywords": ["新加坡", "新传媒"]},
    {"name": "影视轮播", "icon": "🎬", "keywords": ["轮播", "影视轮播", "电影轮播"]}
]
# =================================================================

def classify_channel(name):
    """自动分类频道"""
    name_lower = name.lower()
    for cat in CATEGORIES:
        for kw in cat["keywords"]:
            if kw.lower() in name_lower:
                return cat["name"]
    return "其他频道"

def parse_all_formats(lines):
    """全格式解析，兼容#EXTINF、纯链接、逗号分隔等所有源格式"""
    channels = []
    seen_urls = set()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # 情况1：标准#EXTINF格式
        if line.startswith("#EXTINF:"):
            name = line.split(",")[-1].strip()
            if i + 1 < len(lines):
                url = lines[i+1].strip()
                if url.startswith(("http://", "https://")) and url not in seen_urls:
                    seen_urls.add(url)
                    channels.append((name, url))
            i += 2
        # 情况2：逗号分隔格式（频道名,链接）
        elif "," in line and not line.startswith("#"):
            parts = line.split(",", 1)
            if len(parts) == 2:
                name = parts[0].strip()
                url = parts[1].strip()
                if url.startswith(("http://", "https://")) and url not in seen_urls:
                    seen_urls.add(url)
                    channels.append((name, url))
            i += 1
        # 情况3：纯链接格式
        elif line.startswith(("http://", "https://")) and line not in seen_urls:
            seen_urls.add(line)
            channels.append((f"未知频道_{len(channels)+1}", line))
            i += 1
        else:
            i += 1
    return channels

def main():
    print("🔄 正在读取本地「直播源.txt」，自动分类+去重...")

    # 1. 只读取你本地的直播源.txt，不做任何远程请求，绝对不会失败
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 错误：找不到本地文件 {INPUT_FILE}")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] 错误：{INPUT_FILE} 不存在\n")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        raw_content = f.read()
        lines = raw_content.splitlines()
    print(f"✅ 成功读取本地文件，共 {len(lines)} 行")

    # 2. 全格式解析频道，去重
    channels = parse_all_formats(lines)
    print(f"✅ 解析成功，共 {len(channels)} 个有效频道（已去重）")

    # 3. 按分类分组
    categorized = {cat["name"]: [] for cat in CATEGORIES}
    categorized["其他频道"] = []

    for name, url in channels:
        cat_name = classify_channel(name)
        categorized[cat_name].append((name, url))

    # 4. 生成分类好的M3U
    m3u_content = ["#EXTM3U x-tvg-url=\"https://epg.112114.xyz/epg.xml.gz\""]

    # 按你要的顺序写入分类
    for cat in CATEGORIES:
        cat_name = cat["name"]
        if not categorized[cat_name]:
            continue
        for name, url in categorized[cat_name]:
            m3u_content.append(f'#EXTINF:-1 group-title="{cat_name}",{name}')
            m3u_content.append(url)

    # 写入其他频道
    if categorized["其他频道"]:
        for name, url in categorized["其他频道"]:
            m3u_content.append(f'#EXTINF:-1 group-title="其他频道",{name}')
            m3u_content.append(url)

    # 5. 写入最终iptv.m3u
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_content) + "\n")

    # 6. 写分类统计日志
    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 本地源分类更新完成\n"
    for cat in CATEGORIES:
        log_msg += f"  {cat['name']}：{len(categorized[cat['name']])} 个\n"
    log_msg += f"  其他频道：{len(categorized['其他频道'])} 个\n"
    log_msg += "----------------------------------------\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_msg)
    print(log_msg)

if __name__ == "__main__":
    main()
