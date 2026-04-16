#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直播源抓取脚本
从公开 IPTV 源获取有效频道，确保后续处理有真实可用的流地址
"""

import requests

OUTPUT = "./migu.m3u"
PUBLIC_SOURCES = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u",
    "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/global.m3u",
    "https://mirror.ghproxy.com/https://raw.githubusercontent.com/YueChan/Live/main/IPTV.m3u",
    "https://raw.githubusercontent.com/Meroser/IPTV/main/IPTV.m3u"
]

def fetch_lines_from_url(url):
    lines = []
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = "utf-8"
        raw_lines = r.text.splitlines()
        i = 0
        while i < len(raw_lines):
            line = raw_lines[i].strip()
            if line.startswith("#EXTINF") and i + 1 < len(raw_lines):
                url_line = raw_lines[i + 1].strip()
                if url_line and not url_line.startswith("#"):
                    lines.append(line)
                    lines.append(url_line)
                i += 2
            else:
                i += 1
        print(f"  从 {url} 获取 {len(lines)//2} 个频道")
    except Exception as e:
        print(f"  抓取失败 {url}: {e}")
    return lines

def main():
    all_lines = ["#EXTM3U"]
    seen_urls = set()
    for src in PUBLIC_SOURCES:
        fetched = fetch_lines_from_url(src)
        i = 0
        while i < len(fetched):
            extinf, url = fetched[i], fetched[i+1]
            if url not in seen_urls:
                seen_urls.add(url)
                all_lines.append(extinf)
                all_lines.append(url)
            i += 2
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(all_lines))
    print(f"\n✅ 总计抓取有效频道 {len(all_lines)//2} 个，已保存至 {OUTPUT}")

if __name__ == "__main__":
    main()