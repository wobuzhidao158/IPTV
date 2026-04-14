import os
import time
import requests
from typing import List, Dict

# -------------------------- 配置区 --------------------------
# 咪咕鉴权配置（从GitHub Secrets读取）
MIGU_UID = os.getenv("MIGU_UID", "")
MIGU_TOKEN = os.getenv("MIGU_TOKEN", "")
# 最大重试次数
MAX_RETRY = 3
# 重试间隔（秒）
RETRY_DELAY = 2
# 私源文件路径（优先加载）
PRIVATE_SOURCE_PATH = "./private.m3u"
# 输出文件路径
OUTPUT_PATH = "./output.m3u"
# 咪咕频道配置（ID对应频道，可按需增删）
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
# -------------------------- 工具函数 --------------------------
def get_migu_stream(channel_id: str, channel_name: str) -> str:
    """获取咪咕直播流，带3次重试"""
    api_url = "https://api.miguvideo.com/v1.0/live/playurl"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://tv.miguvideo.com/",
        "Origin": "https://tv.miguvideo.com"
    }
    params = {
        "cid": channel_id,
        "uid": MIGU_UID,
        "token": MIGU_TOKEN,
        "quality": "sh"  # sh=1080P，可改为hd/SD切换清晰度
    }

    for retry in range(1, MAX_RETRY + 1):
        try:
            resp = requests.get(api_url, headers=headers, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0 and data.get("data", {}).get("url"):
                    print(f"✅ {channel_name} 尝试{retry}成功")
                    return data["data"]["url"]
                print(f"⚠️ {channel_name} 尝试{retry}失败，响应：{data.get('msg', '未知错误')}")
            else:
                print(f"⚠️ {channel_name} 尝试{retry}失败，状态码：{resp.status_code}")
        except Exception as e:
            print(f"⚠️ {channel_name} 尝试{retry}失败，异常：{str(e)}")
        time.sleep(RETRY_DELAY)
    
    print(f"❌ {channel_name} 全部尝试失败，标记为失效")
    return "https://example.com/invalid"

def load_private_source() -> List[str]:
    """加载私源M3U，优先保留"""
    if not os.path.exists(PRIVATE_SOURCE_PATH):
        print(f"⚠️ 私源文件{PRIVATE_SOURCE_PATH}不存在，跳过加载")
        return []
    with open(PRIVATE_SOURCE_PATH, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    # 过滤掉#EXTM3U头，避免重复
    return [line for line in lines if not line.startswith("#EXTM3U")]

# -------------------------- 主逻辑 --------------------------
if __name__ == "__main__":
    print("🚀 开始执行私源优先+咪咕源自动更新任务")
    
    # 1. 加载私源
    private_lines = load_private_source()
    
    # 2. 生成咪咕源
    migu_lines = ["#EXTINF:-1 group-title=\"咪咕1080P\",【咪咕1080P】央卫总控"]
    invalid_lines = []
    
    for name, cid in MIGU_CHANNELS.items():
        url = get_migu_stream(cid, name)
        if url == "https://example.com/invalid":
            line = f"#EXTINF:-1 group-title=\"咪咕1080P失效\",{name}【源失效】\n{url}"
            invalid_lines.append(line)
        else:
            line = f"#EXTINF:-1 group-title=\"咪咕1080P\",{name}\n{url}"
            migu_lines.append(line)
    
    # 3. 合并输出（私源优先 + 咪咕有效源 + 咪咕失效源）
    output_lines = ["#EXTM3U"] + private_lines + migu_lines + invalid_lines
    
    # 4. 写入文件
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines) + "\n")
    
    print(f"✅ 任务完成，输出文件：{OUTPUT_PATH}")
