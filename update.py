# -*- coding: utf-8 -*-
# 永久自动拉取你的专属直播源链接 + 自动检测有效 + 自动生成最新M3U
import os
import requests
from datetime import datetime

# ====================== 你的专属链接（已内置！）======================
YOUR_REMOTE_TXT_URL = "http://zhibo.cc.cd/api.php?token=BVna62di&type=txt"
# ====================================================================

INPUT_FILE = "直播源.txt"
OUTPUT_FILE = "iptv.m3u"
LOG_FILE = "update_log.txt"
TIMEOUT = 5

def check_url(url):
    try:
        res = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        return res.status_code in (200, 301, 302)
    except:
        return False

def main():
    print("🔄 正在从你的专属链接拉取最新直播源...")

    # 1. 拉取你给的远程最新源
    try:
        resp = requests.get(YOUR_REMOTE_TXT_URL, timeout=15)
        resp.encoding = "utf-8"
        lines = resp.text.splitlines()
    except:
        print("❌ 拉取失败，使用本地缓存")
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

    # 2. 保存到本地
    with open(INPUT_FILE, "w", encoding="utf-8") as f:
        f.write(resp.text)

    # 3. 提取有效链接 + 去重 + 检测存活
    valid = []
    seen = set()
    bad = 0

    for line in lines:
        line = line.strip()
        if "," in line:
            parts = line.split(",", 1)
            if len(parts) == 2:
                name = parts[0].strip()
                url = parts[1].strip()
                if url.startswith(("http://", "https://")):
                    if url not in seen:
                        seen.add(url)
                        if check_url(url):
                            valid.append((name, url))
                        else:
                            bad += 1

    # 4. 生成标准M3U
    m3u = ["#EXTM3U"]
    for name, url in valid:
        m3u.append(f'#EXTINF:-1 ,{name}')
        m3u.append(url)

    # 5. 写入最终文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    # 6. 日志
    log = f"[{datetime.now()}] 拉取成功 | 有效源：{len(valid)} | 失效源：{bad}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log)
    print(log)

if __name__ == "__main__":
    main()
