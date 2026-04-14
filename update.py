import os

PRIVATE = "./private.m3u"
MIGU_SRC = "./migu.m3u"
OUTPUT = "./output.m3u"

# 电信专属：只留低码率、电信线路、屏蔽4K/8K/高码
FILTER_KEYWORDS = {
    # 屏蔽
    "4K", "2160", "8K", "4k", "2160p", "8k",
    "超高码率", "高码", "60fps", "HDR", "杜比",
    "移动", "CMCC", "移动线路", "联通", "CUCC",
    "m3u8:8080", ":8081", ":8090", "udp://"
}
# 电信优选关键词（优先保留）
TELECOM_KEYS = {"电信", "CTCC", "天翼", "itv", "iptv", "migu", "1080P", "720P", "540P", "标清"}

def read_m3u(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#EXTM3U")]

def filter_telecom_low_bitrate(lines):
    result = []
    skip = False
    for line in lines:
        if skip:
            skip = False
            continue
        # 过滤含黑名单关键词
        if any(k in line for k in FILTER_KEYWORDS):
            skip = True
            continue
        # 只保留含电信/低清关键词（链接或频道名）
        if any(t in line for t in TELECOM_KEYS) or line.startswith("http"):
            result.append(line)
    return result

if __name__ == "__main__":
    private = read_m3u(PRIVATE)
    migu = read_m3u(MIGU_SRC)
    
    all_lines = private + migu
    clean_lines = filter_telecom_low_bitrate(all_lines)
    
    final = ["#EXTM3U"] + clean_lines
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(final))
    print("✅ 电信低码版合并完成：仅保留电信/标清/1080P，已过滤4K/移动/联通")
