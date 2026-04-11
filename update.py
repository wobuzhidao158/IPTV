# -*- coding: utf-8 -*-
# 极速版：只拉取最新源+去重+生成M3U，10秒跑完，零超时
import os
import requests
from datetime import datetime

# 你的专属拉取链接（已内置）
YOUR_REMOTE_TXT_URL = "http://zhibo.cc.cd/api.php?token=BVna62di&type=txt"

INPUT_FILE = "直播源.txt"
OUTPUT_FILE = "iptv.m3u"
LOG_FILE = "update_log.txt"

def main():
    print("🔄 极速拉取最新直播源...")

    # 1. 拉取你的专属最新源（3秒内完成）
    try:
        resp = requests.get(YOUR_REMOTE_TXT_URL, timeout=10)
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

    # 3. 极速去重（毫秒级完成，不做耗时检测）
    seen = set()
    valid_lines = []
    for line in lines:
        line_stripped = line.strip()
        if line_stripped and line_stripped not in seen:
            seen.add(line_stripped)
            valid_lines.append(line)

    # 4. 生成标准M3U（兼容所有播放器）
    m3u_content = ["#EXTM3U"]
    # 直接复用你源里的频道名+链接，不修改格式
    m3u_content.extend(valid_lines)

    # 5. 写入最终iptv.m3u
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_content) + "\n")

    # 6. 写日志
    log = f"[{datetime.now()}] 极速更新完成 | 原始行数：{len(lines)} | 去重后：{len(valid_lines)}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log)
    print(log)

if __name__ == "__main__":
    main()
