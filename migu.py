import requests
import os
import time

# 配置
uid = os.getenv("MIGU_UID")
token = os.getenv("MIGU_TOKEN")
rate = "3"  # 3=1080P 高清
max_retries = 3  # 失效重试次数

# 咪咕央卫核心频道 (CCTV1-15 + 主流卫视)
channel_list = [
    {"name": "CCTV1综合", "cid": "689081"},
    {"name": "CCTV2财经", "cid": "689082"},
    {"name": "CCTV3综艺", "cid": "689083"},
    {"name": "CCTV4中文国际", "cid": "689084"},
    {"name": "CCTV5体育", "cid": "689085"},
    {"name": "CCTV6电影", "cid": "689086"},
    {"name": "CCTV7军事农业", "cid": "689087"},
    {"name": "CCTV8电视剧", "cid": "689088"},
    {"name": "CCTV9纪录", "cid": "689089"},
    {"name": "CCTV10科教", "cid": "689090"},
    {"name": "CCTV11戏曲", "cid": "689091"},
    {"name": "CCTV12社会与法", "cid": "689092"},
    {"name": "CCTV13新闻", "cid": "689093"},
    {"name": "CCTV15音乐", "cid": "689094"},
    {"name": "东方卫视", "cid": "689351"},
    {"name": "浙江卫视", "cid": "689349"},
    {"name": "湖南卫视", "cid": "689347"},
    {"name": "江苏卫视", "cid": "689348"},
    {"name": "北京卫视", "cid": "689350"},
    {"name": "广东卫视", "cid": "689355"},
    {"name": "深圳卫视", "cid": "689357"}
]

def get_play_url_with_retry(cid):
    """带重试机制的URL获取"""
    for attempt in range(max_retries):
        try:
            res = requests.get(
                url="https://api.miguvideo.com/miguvideo/play/url",
                params={
                    "channelId": cid,
                    "userId": uid,
                    "token": token,
                    "rateType": rate
                },
                timeout=15
            )
            data = res.json()
            if data.get("code") == 200 and data.get("data", {}).get("url"):
                return data["data"]["url"]
            print(f"⏱️ 尝试 {attempt+1} 失败，响应: {data.get('msg')}")
        except Exception as e:
            print(f"⏱️ 尝试 {attempt+1} 异常: {str(e)[:50]}")
        
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # 指数退避
    
    return None

def main():
    m3u_content = "#EXTM3U\n#EXTINF:-1 group-title=\"咪咕1080P\",【咪咕1080P】央卫总控\n"
    
    successful = 0
    total = len(channel_list)
    
    for ch in channel_list:
        print(f"🎬 处理 {ch['name']}...")
        url = get_play_url_with_retry(ch["cid"])
        
        if url:
            m3u_content += f'#EXTINF:-1 group-title=\"咪咕1080P\",{ch["name"]}\n{url}\n'
            successful += 1
            print(f"✅ 成功")
        else:
            m3u_content += f'#EXTINF:-1 group-title=\"咪咕1080P失效\",{ch["name"]}【源失效】\nhttps://example.com/invalid\n'
            print(f"❌ 全部尝试失败")
    
    # 写入
    with open("migu.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    
    print(f"\n📊 咪咕1080P源生成完成 | 成功: {successful}/{total} | 总计: {total}")

if __name__ == "__main__":
    main()
