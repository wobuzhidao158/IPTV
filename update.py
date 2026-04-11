# -*- coding: utf-8 -*-
# 1:1还原分类样式 全自动直播源分类脚本
import os
import requests
from datetime import datetime

# 你的专属拉取链接（已内置，不用改）
YOUR_REMOTE_TXT_URL = "http://zhibo.cc.cd/api.php?token=BVna62di&type=txt"

INPUT_FILE = "直播源.txt"
OUTPUT_FILE = "iptv.m3u"
LOG_FILE = "update_log.txt"

# ====================== 1:1匹配你图里的分类规则 ======================
# 分类顺序、分组名完全和你截图一致，关键词精准匹配
CATEGORIES = [
    {
        "name": "央视频道",
        "icon": "📺",
        "keywords": ["CCTV", "央视", "cctv", "中央电视台"]
    },
    {
        "name": "卫视频道",
        "icon": "📺",
        "keywords": ["卫视", "江苏", "浙江", "东方", "湖南", "北京", "山东", "安徽", "湖北", "广东", "深圳", "天津", "重庆", "四川", "河南", "河北", "辽宁", "吉林", "黑龙江"]
    },
    {
        "name": "电影频道",
        "icon": "🎬",
        "keywords": ["电影", "影院", "院线", "影视", "剧场"]
    },
    {
        "name": "儿童频道",
        "icon": "👦",
        "keywords": ["少儿", "儿童", "卡通", "动画", "动漫", "宝贝"]
    },
    {
        "name": "香港频道",
        "icon": "🇭🇰",
        "keywords": ["香港", "TVB", "ViuTV", "香港开电视", "香港国际台"]
    },
    {
        "name": "澳门频道",
        "icon": "🇲🇴",
        "keywords": ["澳门", "澳广视", "澳门莲花"]
    },
    {
        "name": "台湾频道",
        "icon": "🌊",
        "keywords": ["台湾", "中天", "东森", "纬来", "民视", "三立"]
    },
    {
        "name": "新加坡",
        "icon": "🇸🇬",
        "keywords": ["新加坡", "新传媒"]
    },
    {
        "name": "影视轮播",
        "icon": "🎬",
        "keywords": ["轮播", "影视轮播", "电影轮播", "剧集轮播"]
    }
]
# ====================================================================

def classify_channel(name):
    """根据频道名匹配分类，完全对应你要的分组"""
    name_lower = name.lower()
    for cat in CATEGORIES:
        for kw in cat["keywords"]:
            if kw.lower() in name_lower:
                return cat["name"]
    return "其他频道"  # 未匹配的归为其他

def main():
    print("🔄 正在拉取最新直播源，1:1还原分类样式...")

    # 1. 拉取你的专属最新源
    try:
        resp = requests.get(YOUR_REMOTE_TXT_URL, timeout=15)
        resp.encoding = "utf-8"
        raw_content = resp.text
        lines = raw_content.splitlines()
        print(f"✅ 拉取成功，共 {len(lines)} 行")
    except Exception as e:
        print(f"❌ 拉取失败：{str(e)}，使用本地缓存")
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            raw_content = f.read()
            lines = raw_content.splitlines()

    # 2. 保存到本地直播源.txt
    with open(INPUT_FILE, "w", encoding="utf-8") as f:
        f.write(raw_content)

    # 3. 解析频道+去重
    channels = []
    seen_urls = set()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            # 提取频道名
            name = line.split(",")[-1].strip()
            # 下一行是链接
            if i + 1 < len(lines):
                url = lines[i+1].strip()
                if url.startswith(("http://", "https://")) and url not in seen_urls:
                    seen_urls.add(url)
                    channels.append((name, url))
            i += 2
        else:
            i += 1

    print(f"✅ 去重后剩余 {len(channels)} 个有效频道")

    # 4. 按分类分组（顺序完全和你截图一致）
    categorized = {}
    # 初始化所有分类
    for cat in CATEGORIES:
        categorized[cat["name"]] = []
    categorized["其他频道"] = []

    # 分类匹配
    for name, url in channels:
        cat_name = classify_channel(name)
        categorized[cat_name].append((name, url))

    # 5. 生成1:1还原分类的标准M3U（完美适配播放器分组显示）
    m3u_content = ["#EXTM3U x-tvg-url=\"https://epg.112114.xyz/epg.xml.gz\""]

    # 按你截图的顺序写入分类
    for cat in CATEGORIES:
        cat_name = cat["name"]
        if not categorized[cat_name]:
            continue
        # 写入该分类下的所有频道
        for name, url in categorized[cat_name]:
            m3u_content.append(f'#EXTINF:-1 group-title="{cat_name}",{name}')
            m3u_content.append(url)

    # 写入其他频道
    if categorized["其他频道"]:
        m3u_content.append(f'#EXTINF:-1 group-title="其他频道",其他频道')
        for name, url in categorized["其他频道"]:
            m3u_content.append(f'#EXTINF:-1 group-title="其他频道",{name}')
            m3u_content.append(url)

    # 6. 写入最终iptv.m3u
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_content) + "\n")

    # 7. 写分类统计日志
    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 1:1分类更新完成\n"
    for cat in CATEGORIES:
        log_msg += f"  {cat['name']}：{len(categorized[cat['name']])} 个\n"
    log_msg += f"  其他频道：{len(categorized['其他频道'])} 个\n"
    log_msg += "----------------------------------------\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_msg)
    print(log_msg)

if __name__ == "__main__":
    main()
