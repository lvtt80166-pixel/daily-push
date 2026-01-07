import requests
import json
from datetime import datetime

# ==================== 👇 配置区域 👇 ====================
# 1. 已更换为官方稳定接口 (解决了之前的报错问题)
API_URL = "https://hot.imsyy.top" 

# 2. 你的飞书 Webhook 地址 (已帮你填好)
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/f241b8ab-434f-48f4-997c-5d8437a3f9e1"
# ==========================================================

def get_hot_list(type_name):
    """去数据中心拿数据"""
    try:
        # 这里的 headers 是为了伪装成浏览器，防止被拦截
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # 发送请求
        resp = requests.get(f"{API_URL}/{type_name}", headers=headers, timeout=30)
        
        if resp.status_code == 200:
            # 成功！只取前 10 条
            return resp.json().get('data', [])[:10]
        else:
            print(f"[{type_name}] 获取失败，状态码: {resp.status_code}")
            
    except Exception as e:
        print(f"获取 {type_name} 出错: {e}")
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
    try:
        requests.post(WEBHOOK_URL, headers=headers, data=json.dumps(data))
    except Exception as e:
        print(f"发送飞书失败: {e}")

def main():
    print("🚀 开始抓取数据...")
    weibo = get_hot_list("weibo")
    zhihu = get_hot_list("zhihu")
    
    # 拼接文案
    today = datetime.now().strftime("%Y-%m-%d")
    msg = f"📅 **{today}**\n\n"
    
    if weibo:
        msg += "🔴 **微博热搜 Top10**\n"
        for i, item in enumerate(weibo):
            # 格式: 1. [标题](链接) 热度
            title = item.get('title', '无标题')
            url = item.get('url', '#')
            hot = item.get('hot', '')
            msg += f"{i+1}. [{title}]({url})  `{hot}`\n"
    
    if zhihu:
        msg += "\n🔵 **知乎热榜 Top10**\n"
        for
