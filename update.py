import requests
import os

# ===================== 配置 =====================
LOCAL_FILE = "直播源.txt"
OUTPUT_FILE = "iptv.m3u"
NET_URL = "https://raw.githubusercontent.com/wobuzhidao158/IPTV/main/iptv.m3u"

# 【完全按你要求的分类+顺序】
CATEGORIES = {
    "📶央视频道": ["CCTV", "央视", "CGTN"],
    "📶卫视频道": ["卫视", "北京", "天津", "河北", "山西", "内蒙古",
                   "辽宁", "吉林", "黑龙江", "上海", "江苏", "浙江",
                   "安徽", "福建", "江西", "山东", "河南", "湖北",
                   "湖南", "广东", "广西", "海南", "重庆", "四川",
                   "贵州", "云南", "西藏", "陕西", "甘肃", "青海",
                   "宁夏", "新疆", "深圳", "厦门"],
    "📺4K8K频道": ["4K", "8K", "UHD", "2160p", "超高清"],
    "🎥影视频道": ["电影", "影院", "影视", "剧场", "纪录", "科教", "财经"],
    "🧒少儿频道": ["少儿", "儿童", "动画", "卡通"],
    "🇭🇰香港频道": ["TVB", "翡翠", "明珠", "香港", "凤凰", "ViuTV"],
    "🇲🇴澳门频道": ["澳门", "澳广视", "TDM", "澳亚"],
    "🇹🇼台湾频道": ["台视", "中视", "华视", "民视", "公视", "三立", "东森",
                   "中天", "TVBS", "年代", "纬来", "台湾"],
    "🇸🇬新加坡频道": ["新传媒", "星和", "新电信", "新加坡", "Mediacorp"],
    "其他频道": []
}

# ===================== 核心函数 =====================
def get_category(name):
    # 按优先级匹配（先具体后通用）
    priority = ["🇸🇬新加坡频道", "🇹🇼台湾频道", "🇲🇴澳门频道", "🇭🇰香港频道",
                "📺4K8K频道", "🧒少儿频道", "🎥影视频道", "📶央视频道", "📶卫视频道"]
    for cat in priority:
        for kw in CATEGORIES[cat]:
            if kw.lower() in name.lower():
                return cat
    return "其他频道"

# ===================== 主逻辑 =====================
# 1. 读取本地源（优先保留）
local_channels = []
if os.path.exists(LOCAL_FILE):
    with open(LOCAL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "," in line and not line.startswith("#"):
                name, url = line.split(",", 1)
                name = name.strip()
                url = url.strip()
                if url.startswith("http"):
                    local_channels.append((name, url))

# 2. 抓取网络源补充
net_channels = []
try:
    resp = requests.get(NET_URL, timeout=10)
    lines = resp.text.splitlines()
    i = 0
    while i < len(lines):
        l = lines[i].strip()
        if l.startswith("#EXTINF"):
            name = l.split(",")[-1].strip()
            if i + 1 < len(lines):
                url = lines[i+1].strip()
                if url.startswith("http"):
                    net_channels.append((name, url))
                    i += 2
                    continue
        i += 1
except:
    pass

# 3. 合并去重（本地优先）
all_channels = []
exist_names = set()
for name, url in local_channels + net_channels:
    if name not in exist_names:
        all_channels.append((name, url))
        exist_names.add(name)

# 4. 按分类分组
groups = {cat: [] for cat in CATEGORIES.keys()}
for name, url in all_channels:
    cat = get_category(name)
    groups[cat].append((name, url))

# 5. 输出带分类的标准M3U
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write('#EXTM3U x-tvg-url="https://epg.112114.xyz/epg.xml.gz"\n')
    # 严格按你指定的顺序输出分类
    for cat in CATEGORIES.keys():
        for name, url in groups[cat]:
            f.write(f'#EXTINF:-1 group-title="{cat}",{name}\n{url}\n')

# 控制台输出统计
print(f"✅ 本地源：{len(local_channels)} 个")
print(f"✅ 网络源：{len(net_channels)} 个")
print(f"✅ 总频道：{len(all_channels)} 个")
print("\n📊 分类统计：")
for cat in CATEGORIES.keys():
    if groups[cat]:
        print(f"  {cat}: {len(groups[cat])} 个")
