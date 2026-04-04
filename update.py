import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 关闭SSL证书校验警告，解决报错
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# -------------------------- 只改这两行 --------------------------
url = "http://zhibo.cc.cd/api.php?token=OawLE8oN&type=m3u"
filename = "直播源"
# ----------------------------------------------------------------

try:
    # 拉取直播源，跳过SSL证书校验
    response = requests.get(url, verify=False, timeout=15)
    response.raise_for_status()  # 检查HTTP状态码（200才会继续）

    # 写入文件
    with open(filename, "w", encoding="utf-8") as f:
        f.write(response.text)
    print("✅ 直播源更新成功！")

except Exception as e:
    # 所有错误都会在这里打印出来，方便你排查
    print(f"❌ 更新失败，错误详情：{type(e).__name__}: {e}")
    exit(1)
