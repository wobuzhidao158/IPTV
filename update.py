import os

PRIVATE = "./private.m3u"
MIGU_SRC = "./migu.m3u"
OUTPUT = "./output.m3u"

# 黑名单：过滤4K/8K/高码/非电信源
FILTER_KEYWORDS = {
    "4K", "2160", "8K", "4k", "2160p", "8k",
    "超高码率", "高码", "60fps", "HDR", "杜比",
    "移动", "CMCC", "移动线路", "联通", "CUCC",
    "udp://", ":8080", ":8081", ":8090"
}
# 白名单：优先保留电信/低码/1080P源
TELECOM_KEYS = {"电信", "CTCC", "天翼", "itv", "iptv", "migu", "1080P", "720P", "540P", "标清"}

def read_m3u(path):
    if not os.path.exists(path):
        print(f"⚠️  未找到文件: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#EXTM3U")]

def filter_telecom_low_bitrate(lines):
    result = []
    skip_next = False
    for line in lines:
        # 跳过被标记的下一行（链接行）
        if skip_next:
            skip_next = False
            continue
        # 命中黑名单，跳过当前+下一行
        if any(k in line for k in FILTER_KEYWORDS):
            skip_next = True
            continue
        # 命中白名单或为链接行，保留
        if any(t in line for t in TELECOM_KEYS) or line.startswith("http"):
            result.append(line)
    return result

if __name__ == "__main__":
    # 1. 读取私源+咪咕源
    private = read_m3u(PRIVATE)
    migu = read_m3u(MIGU_SRC)
    
    # 2. 私源优先合并，再过滤
    all_lines = private + migu
    clean_lines = filter_telecom_low_bitrate(all_lines)
    
    # 3. 兜底保护：过滤后源过少，直接用原始源
    if len(clean_lines) < 15:
        print("⚠️  过滤后源过少，回退为原始合并模式")
        clean_lines = private + migu
    
    # 4. 写入最终文件
    final = ["#EXTM3U"] + clean_lines
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(final))
    
    print(f"✅ 合并完成：私源优先，仅保留电信/1080P源，共{len(clean_lines)}个频道")
