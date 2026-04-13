import os
import re
import time
import requests
from datetime import datetime

# ===================== 配置区 =====================
CHECK_TIMEOUT = 10
LOCAL_TXT = "直播源.txt"
OUT_M3U = "直播汇总_全分类版.m3u"
LOG_TXT = "更新日志.txt"

# 全网最全源（含港澳台+新加坡+国际）
NETWORK_SOURCES = [
    # 国内央视卫视
    "https://raw.githubusercontent.com/longtian1024/iptv/main/tv.txt",
    "https://raw.githubusercontent.com/ssjunjie1/IPTV/main/IPTV.txt",
    "https://raw.githubusercontent.com/longg0201/iptv/main/tv.txt",
    "https://raw.githubusercontent.com/860466147/iptv/master/tv.txt",
    # 港澳台专用
    "https://raw.githubusercontent.com/Ftindy/IPTV-URL/main/IPTV.m3u",
    "https://raw.githubusercontent.com/GuoQiAiLi/IPTV/main/IPTV.m3u",
    "https://raw.githubusercontent.com/YueChan/Live/main/IPTV.m3u",
    # 新加坡+国际
    "https://live.fanmingming.com/tv/m3u/global.m3u",
    "https://raw.githubusercontent.com/Repcz/Telegram/main/IPTV.m3u"
]

# 【终极全分类】精准匹配所有频道
CATEGORIES = {
    "📺央视频道": ["CCTV", "央视", "CGTN", "中国环球电视网"],
    "📺卫视频道": ["卫视", "北京", "天津", "河北", "山西", "内蒙古",
                   "辽宁", "吉林", "黑龙江", "上海", "江苏", "浙江",
                   "安徽", "福建", "江西", "山东", "河南", "湖北",
                   "湖南", "广东", "广西", "海南", "重庆", "四川",
                   "贵州", "云南", "西藏", "陕西", "甘肃", "青海",
                   "宁夏", "新疆", "深圳", "厦门", "山东教育"],
    "🎥4K频道": ["4K", "8K", "UHD", "2160p", "超高清"],
    "🎬影视频道": ["电影", "影院", "影视", "剧场", "纪录", "科教", "财经"],
    "🧒少儿频道": ["少儿", "儿童", "动画", "卡通", "动漫"],
    "🇭🇰香港频道": ["TVB", "翡翠", "明珠", "香港", "凤凰", "ViuTV", "NowTV"],
    "🇲🇴澳门频道": ["澳门", "澳广视", "TDM", "澳亚"],
    "🇹🇼台湾频道": ["台视", "中视", "华视", "民视", "公视", "三立", "东森",
                   "中天", "TVBS", "年代", "壹电视", "纬来", "台湾"],
    "🇸🇬新加坡频道": ["新传媒", "星和", "新电信", "新加坡", "Mediacorp", "StarHub"],
    "🌍国际频道": ["CNN", "BBC", "FOX", "HBO", "Discovery", "国家地理",
                   "ESPN", "NHK", "KBS", "SBS", "MBC", "VOA", "DW"],
    "其他频道": []
}

# 卫视排序规则
PROVINCE_ORDER = [
    "北京", "天津", "河北", "山西", "内蒙古",
    "辽宁", "吉林", "黑龙江", "上海", "江苏",
    "浙江", "安徽", "福建", "江西", "山东",
    "河南", "湖北", "湖南", "广东", "广西", "海南",
    "重庆", "四川", "贵州", "云南", "西藏",
    "陕西", "甘肃", "青海", "宁夏", "新疆"
]

# ===================== 核心函数 =====================
def clean_name(name):
    name = re.sub(r'[\[\(（【].*?[\]\)）】]', '', name)
    name = re.sub(r'\b\d+[Pp]\b', '', name)
    name = re.sub(r'\b(HD|FHD|SD|高清|超清|标清)\b', '', name, flags=re.I)
    name = re.sub(r'\b(IPV4|IPV6|Not24/7|24/7)\b', '', name, flags=re.I)
    return re.sub(r'\s+', ' ', name).strip()

def get_key(name):
    cn = clean_name(name)
    return re.sub(r'[^\w\u4e00-\u9fff]', '', cn).lower()

def check_alive(url):
    try:
        r = requests.get(url, timeout=CHECK_TIMEOUT, stream=True)
        return r.status_code in (200, 302)
    except:
        return False

def fetch_network_sources():
    channels = {}
    for url in NETWORK_SOURCES:
        try:
            r = requests.get(url, timeout=15)
            lines = r.text.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue
                # 解析txt格式
                if ',' in line and not line.startswith('#'):
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        name, u = parts[0].strip(), parts[1].strip()
                        if u.startswith('http'):
                            key = get_key(name)
                            if key not in channels:
                                channels[key] = (name, u)
                    i += 1
                # 解析m3u格式
                elif line.startswith('#EXTINF'):
                    name = line.split(',')[-1].strip()
                    if i + 1 < len(lines):
                        u = lines[i+1].strip()
                        if u.startswith('http'):
                            key = get_key(name)
                            if key not in channels:
                                channels[key] = (name, u)
                        i += 2
                    else:
                        i += 1
                else:
                    i += 1
        except:
            continue
    return channels

def get_category(name):
    """精准分类，按优先级匹配"""
    # 先匹配最具体的分类
    priority_order = ["🇸🇬新加坡频道", "🇹🇼台湾频道", "🇲🇴澳门频道", "🇭🇰香港频道",
                      "🌍国际频道", "🎥4K频道", "🧒少儿频道", "🎬影视频道",
                      "📺央视频道", "📺卫视频道"]
    for cat in priority_order:
        for kw in CATEGORIES[cat]:
            if kw.lower() in name.lower():
                return cat
    return "其他频道"

def sort_key(name, cat):
    if cat == "📺央视频道":
        m = re.search(r'CCTV[-]?(\d+)', name)
        return int(m.group(1)) if m else 99
    elif cat == "📺卫视频道":
        for idx, p in enumerate(PROVINCE_ORDER):
            if p in name:
                return idx
    return 999

# ===================== 主程序 =====================
def main():
    start = time.time()
    print("🚀 开始生成全分类直播源...")

    # 1. 读取本地所有频道（全部保留）
    local = {}
    if os.path.exists(LOCAL_TXT):
        try:
            with open(LOCAL_TXT, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except:
            with open(LOCAL_TXT, 'r', encoding='gbk') as f:
                lines = f.readlines()

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2:
                    name, url = parts[0].strip(), parts[1].strip()
                    if url.startswith('http'):
                        key = get_key(name)
                        local[key] = (name, url)

    print(f"📂 本地读取：{len(local)} 个频道")

    # 2. 检测本地可用，失效的标记
    valid = {}
    invalid_keys = []
    for key, (name, url) in local.items():
        if check_alive(url):
            valid[key] = (name, url)
        else:
            invalid_keys.append(key)

    print(f"✅ 本地可用：{len(valid)} | ❌ 失效：{len(invalid_keys)}")

    # 3. 抓取全网源补充
    print("🌐 正在抓取全网源...")
    net_channels = fetch_network_sources()
    print(f"🌍 网络源总数：{len(net_channels)}")

    # 补充规则：
    # - 所有分类的失效频道都补充
    # - 港澳台、新加坡、国际频道额外新增
    added = 0
    for key, (name, url) in net_channels.items():
        cat = get_category(name)
        # 优先补充本地失效的
        if key in invalid_keys and key not in valid:
            if check_alive(url):
                valid[key] = (name, url)
                added += 1
        # 额外新增港澳台、新加坡、国际频道
        elif cat in ["🇭🇰香港频道", "🇲🇴澳门频道", "🇹🇼台湾频道", "🇸🇬新加坡频道", "🌍国际频道"]:
            if key not in valid and check_alive(url):
                valid[key] = (name, url)
                added += 1

    print(f"🔄 补充/新增：{added} 个频道")

    # 4. 保存更新后的本地源
    with open(LOCAL_TXT, 'w', encoding='utf-8') as f:
        for name, url in valid.values():
            f.write(f"{name},{url}\n")

    # 5. 全部分类
    groups = {cat: [] for cat in CATEGORIES.keys()}
    for name, url in valid.values():
        cat = get_category(name)
        groups[cat].append((name, url))

    # 6. 组内排序
    for cat in groups:
        groups[cat].sort(key=lambda x: sort_key(x[0], cat))

    # 7. 输出标准M3U
    with open(OUT_M3U, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U x-tvg-url="https://epg.112114.xyz/epg.xml.gz"\n')
        for cat in CATEGORIES.keys():
            if groups[cat]:
                for name, url in groups[cat]:
                    f.write(f'#EXTINF:-1 group-title="{cat}",{name}\n{url}\n')

    # 日志
    elapsed = time.time() - start
    log = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 总频道:{len(valid)} 本地:{len(valid)-added} 新增:{added} 耗时:{elapsed:.1f}s\n"
    with open(LOG_TXT, 'a', encoding='utf-8') as f:
        f.write(log)

    print("\n🎉 全分类直播源生成完成！")
    print(log.strip())
    print("\n📊 分类统计：")
    for cat in CATEGORIES.keys():
        if groups[cat]:
            print(f"  {cat}: {len(groups[cat])} 个")

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    main()