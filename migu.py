import os
import requests
import json

# 咪咕密钥（从GitHub Secrets读取）
MIGU_UID = os.environ.get("MIGU_UID", "")
MIGU_TOKEN = os.environ.get("MIGU_TOKEN", "")

# 🔴 核心：强制指定720P码率，拒绝1080P
QUALITY = "720"  # 可选：540/480，720最稳
OUTPUT = "./migu.m3u"

# 咪咕API（示例，根据你的实际脚本修改，核心是强制720P）
def get_migu_channels():
    headers = {
        "uid": MIGU_UID,
        "token": MIGU_TOKEN,
        "User-Agent": "Migu/1.0"
    }
    # 这里替换成你实际的咪咕频道接口，核心是在请求中指定quality=720
    url = f"https://api.migu.tv/channels?quality={QUALITY}"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.json().get("channels", [])
    except Exception as e:
        print(f"⚠️ 咪咕API请求失败: {e}")
        return []

def generate_m3u(channels):
    m3u = ["#EXTM3U"]
    for ch in channels:
        # 强制720P流地址
        url = ch.get("url_720", "")
        if not url:
            continue
        m3u.append(f'#EXTINF:-1 tvg-name="{ch["name"]}" tvg-id="{ch["id"]}" group-title="咪咕720P"')
        m3u.append(url)
    return m3u

if __name__ == "__main__":
    if not MIGU_UID or not MIGU_TOKEN:
        print("❌ 咪咕UID/TOKEN未配置，请检查GitHub Secrets")
        exit(1)
    channels = get_migu_channels()
    m3u = generate_m3u(channels)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    print(f"✅ 咪咕720P源生成完成，共{len(m3u)//2}个频道")
