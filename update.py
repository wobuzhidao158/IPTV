# 本地读取直播源文件，彻底禁用外网请求
OUTPUT_FILE = "直播源.txt"

# 读取同目录下你已经整理好的【直播源】文件
with open("直播源", "r", encoding="utf-8") as source_file:
    content = source_file.read()

# 将内容写入输出文件，供播放器调用
with open(OUTPUT_FILE, "w", encoding="utf-8") as target_file:
    target_file.write(content)

print("✅ 本地直播源更新完成，无外网请求，无404错误！")
