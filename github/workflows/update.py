# 本地读取直播源文件，彻底不用失效外网接口
OUTPUT_FILE = "直播源.txt"

# 读取同目录下你整理好的【直播源】文件内容
with open("直播源", "r", encoding="utf-8") as f:
    content = f.read()

# 写入输出文件供调用
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 本地直播源读取写入完成，无外网请求！")
