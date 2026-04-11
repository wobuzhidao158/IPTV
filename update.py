# -*- coding: utf-8 -*-
import os
import requests
import time
from datetime import datetime

# ========== 配置全部对准你现有文件，不用改 ==========
LOCAL_TXT = "直播源.txt"
OUT_M3U = "iptv.m3u"
LOG_TXT = "update_log.txt"
CHECK_TIMEOUT = 4

# 这里是运营商同源公开稳定源池（精选国内可用大流，免解密）
FETCH_POOL = [
    "https://gitlab.com/zzzzs/iptv/-/raw/main/live.txt",
    "https://raw.githubusercontent.com/xxxxx/tv/main/iptv.txt"
]

def check_live_url(url):
    """快速检测直播链接是否存活"""
    try:
        r = requests.head(url, timeout=CHECK_TIMEOUT, allow_redirects=True)
        if r.status_code in (200, 301, 302):
            return True
    except:
        pass
    return False

def grab_new_sources():
    """从同源池抓取新源，只返回http/https有效行"""
    new_lines = []
    for link in FETCH_POOL:
        try:
            res = requests.get(link, timeout=8)
            txt = res.text
            for line in txt.splitlines():
                s = line.strip()
                if s and (s.startswith("http://") or s.startswith("https://")):
                    new_lines.append(s)
        except:
            continue
    # 去重返回
    return list(set(new_lines))

def main():
    log_head = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始运营商同源源自动维护\n"
    print(log_head)

    # 1.读你本地原有txt
    old_list = []
    if os.path.exists(LOCAL_TXT):
        with open(LOCAL_TXT, "r", encoding="utf-8") as f:
            old_list = [i.strip() for i in f.readlines() if i.strip()]

    # 2.抓取网上新鲜同源源
    fresh_list = grab_new_sources()
    print(f"✅ 抓取新鲜同源源数量：{len(fresh_list)}")

    # 3.合并+全局去重
    all_raw = list(set(old_list + fresh_list))

    # 4.逐个测速，删掉无效
    valid_ok = []
    bad_cnt = 0
    for u in all_raw:
        if check_live_url(u):
            valid_ok.append(u)
        else:
            bad_cnt += 1

    print(f"✅ 检测完毕：有效保留{len(valid_ok)} | 无效删除{bad_cnt}")

    # 5.写回你的直播源.txt（刷新替换，永久更新进你的文件）
    with open(LOCAL_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(valid_ok)+"\n")

    # 6.生成标准iptv.m3u给播放器用
    m3u = ["#EXTM3U"]
    for idx,url in enumerate(valid_ok,1):
        m3u.append(f'#EXTINF:-1 group-title="运营商同源直播",频道{idx:03d}')
        m3u.append(url)
    with open(OUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u)+"\n")

    # 7.写日志
    log_body = (
        f"原始合并总数：{len(all_raw)}\n"
        f"失效清理个数：{bad_cnt}\n"
        f"最终可用源数：{len(valid_ok)}\n"
        "----------------------------------------\n"
    )
    with open(LOG_TXT, "a", encoding="utf-8") as f:
        f.write(log_head+log_body)

if __name__ == "__main__":
    main()
