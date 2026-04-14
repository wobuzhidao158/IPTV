import os

# 文件路径
PRIVATE = "./private.m3u"
MIGU_SRC = "./migu.m3u"
OUTPUT = "./output.m3u"

def read_m3u(path):
    if not os.path.exists(path):
        return []
    with open(path,"r",encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#EXTM3U")]

if __name__ == "__main__":
    # 读取顺序：私源 > 咪咕
    private = read_m3u(PRIVATE)
    migu = read_m3u(MIGU_SRC)

    # 最终合并
    final = ["#EXTM3U"] + private + migu

    # 写出
    with open(OUTPUT,"w",encoding="utf-8") as f:
        f.write("\n".join(final))
    print("✅ 合并完成：private + migu1080P")
