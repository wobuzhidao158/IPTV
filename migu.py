import requests
import re

OUTPUT = "./migu.m3u"
# 可用的公开源列表
PUBLIC_SOURCES = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u",
    "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/global.m3u",
    "https://agit.ai/iptv/iptv/raw/branch/master/iptv.m3u"
]

def fetch_m3u_lines():
    all_lines = []
    for url in PUBLIC_SOURCES:
        try:
            r = requests.get(url, timeout=10)
            r.encoding = 'utf-8'
            lines = r.text.splitlines()
            # 只保留有效的 EXTINF 和 URL 行
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith('#EXTINF') and i+1 < len(lines):
                    url_line = lines[i+1].strip()
                    if url_line and not url_line.startswith('#'):
                        all_lines.append(line)
                        all_lines.append(url_line)
                    i += 2
                else:
                    i += 1
        except Exception as e:
            print(f"抓取失败 {url}: {e}")
    return all_lines

if __name__ == "__main__":
    lines = fetch_m3u_lines()
    if lines:
        with open(OUTPUT, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n" + "\n".join(lines))
        print(f"✅ 成功抓取 {len(lines)//2} 个频道")
    else:
        print("❌ 未抓取到任何频道，请检查网络")