import os

PRIVATE = "./private.m3u"
MIGU_SRC = "./migu.m3u"
OUTPUT = "./output.m3u"

# 需要过滤的4K/8K关键词
FILTER_KEYWORDS = {"4K", "2160", "8K", "超清4K", "4k", "2160P", "2160p"}

def read_m3u(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#EXTM3U")]

# 过滤掉4K/8K频道
def filter_1080_only(lines):
    result = []
    skip_next = False
    for line in lines:
        # 节目名称行，命中4K关键词则跳过当前+下一条链接
        if any(k in line for k in FILTER_KEYWORDS):
            skip_next = True
            continue
        # 链接行，如果标记跳过则不写入
        if skip_next:
            skip_next = False
            continue
        result.append(line)
    return result

if __name__ == "__main__":
    private = read_m3u(PRIVATE)
    migu = read_m3u(MIGU_SRC)

    # 合并后过滤
    all_lines = private + migu
    clean_lines = filter_1080_only(all_lines)

    final = ["#EXTM3U"] + clean_lines

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(final))
    print("✅ 合并完成：仅保留1080P，已过滤4K/8K")
