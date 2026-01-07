import requests
import json
from datetime import datetime

# ==================== 👇 只要改这就行 👇 ====================
# 1. 填入你的 Vercel 网址 (注意：结尾不要带斜杠 /)
# 例如: "https://daily-hot-api-xxxx.vercel.app"
API_URL = "https://daily-hot-mu-swart.vercel.app" 

# 2. 填入你的 飞书 Webhook 地址
# 例如: "https://open.feishu.cn/open-apis/bot/v2/hook/xxxx"
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/f241b8ab-434f-48f4-997c-5d8437a3f9e1"
# ==========================================================

def get_hot_list(type_name):
    """去数据中心拿数据"""
    try:
        resp = requests.get(f"{API_URL}/{type_name}", timeout=30)
        if resp.status_code == 200:
            # 只取前 10 条
            return resp.json().get('data', [])[:10]
    except Exception as e:
        print(f"获取 {type_name} 失败: {e}")
    return []

def send_feishu(content):
    """把消息发给飞书机器人"""
    headers = {'Content-Type': 'application/json'}
    # 注意：这里的 title 必须包含你设置的关键词 "热搜"
    data = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "template": "blue",
                "title": {
                    "content": "🔥 今日全网热搜选题", 
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": content,
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "note",
                    "elements": [
                        {"content": "数据来源: DailyHotApi", "tag": "plain_text"}
                    ]
                }
            ]
        }
    }
    requests.post(WEBHOOK_URL, headers=headers, data=json.dumps(data))

def main():
    print("开始抓取数据...")
    weibo = get_hot_list("weibo")
    zhihu = get_hot_list("zhihu")
    
    # 拼接文案
    today = datetime.now().strftime("%Y-%m-%d")
    msg = f"📅 **{today}**\n\n"
    
    if weibo:
        msg += "🔴 **微博热搜 Top10**\n"
        for i, item in enumerate(weibo):
            # 格式: 1. [标题](链接) 热度
            msg += f"{i+1}. [{item['title']}]({item['url']})  `{item.get('hot', '')}`\n"
    
    if zhihu:
        msg += "\n🔵 **知乎热榜 Top10**\n"
        for i, item in enumerate(zhihu):
            msg += f"{i+1}. [{item['title']}]({item['url']})\n"
            
    # 发送
    if weibo or zhihu:
        send_feishu(msg)
        print("发送成功！")
    else:
        print("没抓到数据，尴尬了。")

if __name__ == "__main__":
    main()
