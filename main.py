import requests
import json
from datetime import datetime

# ================= 配置区域 =================
API_URL = "https://hot.imsyy.top"
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/f241b8ab-434f-48f4-997c-5d8437a3f9e1"
# ===========================================

def get_hot_list(type_name):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(f"{API_URL}/{type_name}", headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json().get('data', [])[:10]
        else:
            print(f"获取 {type_name} 失败，状态码: {resp.status_code}")
    except Exception as e:
        print(f"获取 {type_name} 出错: {e}")
    return []

def send_feishu(content):
    headers = {'Content-Type': 'application/json'}
    data = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "template": "blue",
                "title": {"content": "🔥 今日全网热搜选题", "tag": "plain_text"}
            },
            "elements": [
                {"tag": "div", "text": {"content": content, "tag": "lark_md"}},
                {"tag": "note", "elements": [{"content": "数据来源: DailyHotApi", "tag": "plain_text"}]}
            ]
        }
    }
    try:
        requests.post(WEBHOOK_URL, headers=headers, data=json.dumps(data))
    except Exception as e:
        print(f"发送飞书失败: {e}")

def main():
    print("🚀 开始抓取...")
    weibo = get_hot_list("weibo")
    zhihu = get_hot_list("zhihu")
    
    today = datetime.now().strftime("%Y-%m-%d")
    msg = f"📅 **{today}**\n\n"
    
    if weibo:
        msg += "🔴 **微博热搜 Top10**\n"
        for i, item in enumerate(weibo):
            title = item.get('title', '无标题').strip()
            url = item.get('url', '#')
            hot = str(item.get('hot', '')).strip()
            msg += f"{i+1}. [{title}]({url}) `{hot}`\n"
    
    if zhihu:
        msg += "\n🔵 **知乎热榜 Top10**\n"
        for i, item in enumerate(zhihu):
            title = item.get('title', '无标题').strip()
            url = item.get('url', '#')
            msg += f"{i+1}. [{title}]({url})\n"
            
    if weibo or zhihu:
        send_feishu(msg)
        print("✅ 发送成功！")
    else:
        print("❌ 没抓到数据，请检查 API 是否可用。")

if __name__ == "__main__":
    main()
