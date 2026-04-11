# -*- coding: utf-8 -*-
# 自动拉取+自动分类+自动去重+自动生成M3U 终极版
import os
import requests
from datetime import datetime

# 你的专属拉取链接（已内置，不用改）
YOUR_REMOTE_TXT_URL = "http://zhibo.cc.cd/api.php?token=BVna62di&type=txt"

INPUT_FILE = "直播源.txt"
OUTPUT_FILE = "iptv.m3u"
LOG_FILE = "update_log.txt"

# ====================== 分类关键词配置（精准匹配，不用改）======================
CATEGORIES = {
    "央视": ["CCTV", "央视", "cctv"],
    "卫视": ["卫视", "江苏", "浙江", "东方", "湖南", "北京", "山东", "安徽", "湖北", "广东", "深圳", "天津", "重庆", "四川", "河南", "河北", "辽宁", "吉林", "黑龙江"],
    "影视": ["影视", "电影", "剧场", "院线", "VIP", "会员", "追剧"],
    "少儿": ["少儿", "卡通", "动画", "动漫", "宝贝", "儿童"],
    "港澳台": ["香港", "澳门", "台湾", "TVB", "ViuTV", "中天", "东森", "纬来", "民视"]
}
# ==============================================================================

def classify_channel(name, url):
    """根据频道名自动分类"""
    name_lower = name.lower()
    for category, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw.lower() in name_lower:
                return category
    return "其他"  # 未匹配到的归为其他

def main():
    print("🔄 正在拉取最新直播源并自动分类...")

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

    # 3. 解析+去重
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

    # 4. 按分类分组
    categorized = {cat: [] for cat in CATEGORIES.keys()}
    categorized["其他"] = []  # 补充其他分组

    for name, url in channels:
        cat = classify_channel(name, url)
        categorized[cat].append((name, url))

    # 5. 生成分类好的标准M3U
    m3u_content = ["#EXTM3U x-tvg-url=\"https://epg.112114.xyz/epg.xml.gz\""]

    # 按顺序写入分类（央视→卫视→影视→少儿→港澳台→其他）
    for cat in ["央视", "卫视", "影视", "少儿", "港澳台", "其他"]:
        if not categorized[cat]:
            continue
        # 写入分类分组
        for name, url in categorized[cat]:
            m3u_content.append(f'#EXTINF:-1 group-title="{cat}",{name}')
            m3u_content.append(url)

    # 6. 写入最终iptv.m3u
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_content) + "\n")

    # 7. 写分类统计日志
    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 分类更新完成\n"
    for cat in ["央视", "卫视", "影视", "少儿", "港澳台", "其他"]:
        log_msg += f"  {cat}：{len(categorized[cat])} 个\n"
    log_msg += "----------------------------------------\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_msg)
    print(log_msg)

if __name__ == "__main__":
    main()
