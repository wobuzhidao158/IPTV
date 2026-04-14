import os

PRIVATE = "./private.m3u"
OUTPUT = "./output.m3u"

# 只过滤4K/8K/非电信，不追加任何其他源
FILTER_KEYWORDS = {"4K", "2160", "8K", "4k", "2160p", "8k", "移动", "联通", "CMCC", "CUCC", "HDR", "杜比"}
REQUIRE_KEYWORDS = {"电信", "CTCC", "itv", "iptv", "1080P", "720P", "标清"}

def read_m3u(path):
    if not os.path.exists(path):
        print(f"⚠️  未找到私源文件: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#EXTM3U")]

def filter_private_only(lines):
    result = []
    skip_next = False
    for line in lines:
        if skip_next:
            skip_next = False
            continue
        # 过滤黑名单关键词
        if any(k in line for k in FILTER_KEYWORDS):
            skip_next = True
            continue
        # 只保留符合要求的私源
        if any(t in line for t in REQUIRE_KEYWORDS) or line.startswith("http"):
            result.append(line)
    return result

if __name__ == "__main__":
    private = read_m3u(PRIVATE)
    clean_lines = filter_private_only(private)
    
    # 兜底：如果过滤后源太少，直接用原始私源
    if len(clean_lines) < 10:
        print("⚠️  过滤后私源过少，直接使用原始私源")
        clean_lines = private
    
    final = ["#EXTM3U"] + clean_lines
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(final))
    print(f"✅ 仅处理私源完成：保留{len(clean_lines)}个电信/1080P频道")
