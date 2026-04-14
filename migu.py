import os
import time
import requests

MIGU_UID = os.getenv("MIGU_UID", "")
MIGU_TOKEN = os.getenv("MIGU_TOKEN", "")
MAX_RETRY = 3
RETRY_DELAY = 2
OUTPUT_PATH = "./migu.m3u"

MIGU_CHANNELS = {
    "CCTV1综合": "3300",
    "CCTV2财经": "3301",
    "CCTV3综艺": "3302",
    "CCTV4中文国际": "3303",
    "CCTV5体育": "3304",
    "CCTV6电影": "3305",
    "CCTV7军事农业": "3306",
    "CCTV8电视剧": "3307",
    "CCTV9纪录": "3308",
    "CCTV10科教": "3309",
    "CCTV11戏曲": "3310",
    "CCTV12社会与法": "3311",
    "CCTV13新闻": "3312",
    "CCTV15音乐": "3313",
    "东方卫视": "3330",
    "浙江卫视": "3331",
    "湖南卫视": "3332",
    "江苏卫视": "3333",
    "北京卫视": "3334",
    "广东卫视": "3335",
    "深圳卫视": "3336"
}

def get_migu_url(cid, name):
    api = "https://api.miguvideo.com/v1.0/live/playurl"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://tv.miguvideo.com"}
    params = {"cid": cid, "uid": MIGU_UID, "token": MIGU_TOKEN, "quality": "sh"}

    for _ in range(MAX_RETRY):
        try:
            res = requests.get(api, headers=headers, params=params, timeout=15)
            data = res.json()
            if data.get("code") == 0 and data["data"].get("url"):
                return data["data"]["url"]
        except:
            pass
        time.sleep(RETRY_DELAY)
    return None

if __name__ == "__main__":
    lines = ["#EXTM3U", "#EXTINF:-1 group-title=\"咪咕1080P\",咪咕1080P高清"]
    for name, cid in MIGU_CHANNELS.items():
        url = get_migu_url(cid, name)
        if url:
            lines.append(f"#EXTINF:-1 group-title=\"咪咕1080P\",{name}")
            lines.append(url)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("✅ migu.m3u 生成完成")
