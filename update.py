import os

PRIVATE = "./private.m3u"
MIGU_SRC = "./migu.m3u"
OUTPUT = "./output.m3u"

# 黑名单：过滤4K/8K/高码/移动联通/危险端口
FILTER_KEYWORDS = {
    "4K", "2160", "8K", "4k", "2160p", "8k",
    "超高码率", "高码", "60fps", "HDR", "杜比",
    "移动", "CMCC", "移动线路", "联通", "CUCC",
    "udp://", ":8080", ":8081", ":8090", ":9000",
    "超清增强", "极致", "蓝光"
}

# 白名单：优先保留电信/低码/1080P
TELECOM_KEYS = {
    "电信", "CTCC", "天翼", "itv", "iptv", 
    "migu", "1080P", "720P", "540P", "标清", "高清"
}

def read_m3u(path):
    if not os.path.exists(path):
        print(f"⚠️  未找到文件: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f]
        # 过滤空行、保留所有内容（后续统一处理）
        return [line for line in lines if line.strip() != ""]

def filter_telecom_low_bitrate(lines):
    result = []
    skip_next = False

    for line in lines:
        if skip_next:
            skip_next = False
            continue
        
        # 黑名单命中：跳过当前行 + 下一行链接
        if any(key in line for key in FILTER_KEYWORDS):
            skip_next = True
            continue
        
        # 规则：
        # 1. 链接全部保留
        # 2. 频道信息行：含白名单 或 常规央视/卫视 直接放行
        if line.startswith("http") or any(t in line for t in TELECOM_KEYS):
            result.append(line)
        else:
            # 普通常规频道不放黑名单也保留，防止误删台
            result.append(line)

    return result

def deduplicate(lines):
    """链接去重，保留第一条"""
    seen_url = set()
    final = []
    for line in lines:
        if line.startswith("http"):
            if line in seen_url:
                continue
            seen_url.add(line)
        final.append(line)
    return final

if __name__ == "__main__":
    # 读取文件
    private = read_m3u(PRIVATE)
    migu = read_m3u(MIGU_SRC)

    # 合并：私源优先
    all_lines = private + migu

    # 过滤 + 去重
    clean_lines = filter_telecom_low_bitrate(all_lines)
    clean_lines = deduplicate(clean_lines)

    # 过滤后过少，直接回退原始合并
    if len(clean_lines) < 15:
        print("⚠️  过滤后源过少，回退为原始合并模式")
        clean_lines = deduplicate(private + migu)

    # 写入标准 M3U
    final_content = ["#EXTM3U"] + clean_lines
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(final_content))

    print(f"✅ 合并完成 | 私源优先 | 仅保留电信低码/1080P | 最终频道数: {len(clean_lines)}")
