# -*- coding: utf-8 -*-
import os
from datetime import datetime

# 严格对应你仓库的文件名：直播源.txt，绝对不能改
INPUT_FILE = "直播源.txt"
OUTPUT_FILE = "iptv.m3u"
LOG_FILE = "update_log.txt"

def main():
    # 检查文件是否存在
    if not os.path.exists(INPUT_FILE):
        print(f"错误：找不到 {INPUT_FILE}，请确认文件名")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 错误：{INPUT_FILE} 不存在\n")
        return

    # 读取直播源
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    print(f"读取原始行数：{len(lines)}")

    # 去重+过滤无效源
    seen = set()
    valid = []
    bad = dup = 0
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#") or not s.startswith(("http://", "https://")):
            bad += 1
            continue
        if s in seen:
            dup += 1
            continue
        seen.add(s)
        valid.append(s)

    print(f"过滤无效源{bad}个，去重{dup}个，有效源{len(valid)}个")

    # 生成标准M3U
    m3u = ["#EXTM3U"]
    for i, url in enumerate(valid, 1):
        m3u.append(f'#EXTINF:-1 group-title="我的直播源",频道{i:03d}')
        m3u.append(url)

    # 写入文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u) + "\n")

    # 写日志
    log = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 原始{len(lines)}行 | 无效{bad} | 重复{dup} | 有效{len(valid)}\n"
    print(log)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log)

if __name__ == "__main__":
    main()
