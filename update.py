# -*- coding: utf-8 -*-
import os
from datetime import datetime

INPUT_FILE = "直播源.txt"
OUTPUT_FILE = "iptv.m3u"
LOG_FILE = "update_log.txt"

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"错误：找不到 {INPUT_FILE}")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] 错误：{INPUT_FILE} 不存在\n")
        return

    # 直接读取原文件，完整保留格式
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 只去重，不做任何过滤，完整保留所有内容
    seen = set()
    unique_lines = []
    dup_count = 0
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)
        else:
            dup_count += 1

    # 直接写入，完全保留原格式
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(unique_lines)

    # 写日志
    log = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 原始{len(lines)}行 | 去重{dup_count}行 | 最终{len(unique_lines)}行\n"
    print(log)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log)

if __name__ == "__main__":
    main()
