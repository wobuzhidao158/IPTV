import os

PRIVATE = "./private.m3u"
MIGU_SRC = "./migu.m3u"
OUTPUT = "./output.m3u"

# 黑名单：过滤4K/高码/非电信
FILTER_KEYWORDS = {"4K", "2160", "8K", "移动", "联通", "HDR", "杜比"}
# 白名单：必须包含这些词才保留（兜底）
REQUIRE_KEYWORDS = {"电信", "CTCC", "itv", "iptv", "migu", "1080P", "720P"}

def read_m3u(path):
    if not os.path.exists(path):
        print(f"⚠️  未找到文件: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]

if __name__ == "__main__":
    private_lines = read_m3u(PRIVATE)
    migu_lines = read_m3u(MIGU_SRC)
    
    final_lines = ["#EXTM3U"]
    
    # 合并所有行
    all_lines = private_lines + migu_lines
    
    skip_next = False
    for i in range(len(all_lines)):
        line = all_lines[i]
        
        # 处理跳过逻辑
        if skip_next:
            skip_next = False
            continue
            
        # 1. 过滤掉包含黑名单关键词的行
        if any(keyword in line for keyword in FILTER_KEYWORDS):
            # 如果是链接行，需要跳过下一行（标题+链接）
            if line.startswith("http"):
                skip_next = True
            continue
            
        # 2. 保留规则（必须含电信/ITV/咪咕/标清）
        # 或者是纯链接（默认认为合法）
        if any(req in line for req in REQUIRE_KEYWORDS) or line.startswith("http"):
            final_lines.append(line)
    
    # 🔴 关键保护：如果生成的源少于10个，直接使用原始源，避免卡顿无台可看
    if len(final_lines) < 15:
        print("⚠️  过滤后源过少，已回退为原始合并模式")
        final_lines = ["#EXTM3U"] + private_lines + migu_lines
    
    # 写入文件（确保覆盖）
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"✅ 成功生成：{len(final_lines)-1} 个频道（电信/1080P专属）")
