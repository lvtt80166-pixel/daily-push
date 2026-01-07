import requests
import json
from datetime import datetime

# ==================== 👇 这里不用动 👇 ====================
# 我们换成了 "韩小韩" 的稳定接口，不再用 Vercel 了
WEIBO_API = "https://api.vvhan.com/api/hotlist/wbHot"
ZHIHU_API = "https://api.vvhan.com/api/hotlist/zhihuHot"

# 你的飞书 Webhook (已填好)
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/f241b8ab-434f-48f4-997c-5d8437a3f9e1"
# ========================================================

def get_data(url, name):
    """通用抓取函数"""
    try:
        # 伪装成普通浏览器
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        print(f"正在连接 {name} ...")
        resp = requests.get(url, headers=headers, timeout=30)
        
        if resp.status_code == 200:
            res_json = resp.json()
            if res_json.get('success') is True:
                # 成功拿到数据
                print(f"✅ {name} 获取成功！")
                return res_json.get('data', [])[:10]
            else:
                print(f"❌ {name} 接口返回失败: {res_json}")
        else:
            print(f"❌ {name} 网络错误: {resp.status_code}")
    except Exception as e:
        print(f"❌ {name} 发生异常: {e}")
    return []

def send_feishu(content):
    headers = {'Content-Type': 'application/json'}
    data = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "template": "blue",
                "title": {"content": "🔥 今日全网热搜 (Vvhan版)", "tag": "plain_text"}
            },
            "elements": [
                {"tag": "div", "text": {"content": content, "tag": "lark_md"}},
                {"tag": "note", "elements": [{"content": "数据来源: 韩小韩API", "tag": "plain_text"}]}
            ]
        }
    }
    try:
        requests.post(WEBHOOK_URL, headers=headers, data=json.dumps(data))
    except Exception as e:
        print(f"发送飞书失败: {e}")

def main():
    print("🚀 任务开始...")
    
    # 1. 抓取
    weibo_list = get_data(WEIBO_API, "微博")
    zhihu_list = get_data(ZHIHU_API, "知乎")
    
    # 2. 拼装文案
    today = datetime.now().strftime("%Y-%m-%d")
    msg = f"📅 **{today}**\n\n"
    
    has_data = False
    
    if weibo_list:
        has_data = True
        msg += "🔴 **微博热搜 Top10**\n"
        for i, item in enumerate(weibo_list):
            title = item.get('title', '无标题').strip()
            url = item.get('url', item.get('link', '#'))
            hot = item.get('hot', '')
            msg += f"{i+1}. [{title}]({url}) `{hot}`\n"
            
    if zhihu_list:
        has_data = True
        msg += "\n🔵 **知乎热榜 Top10**\n"
        for i, item in enumerate(zhihu_list):
            title = item.get('title', '无标题').strip()
            url = item.get('url', item.get('link', '#'))
            msg += f"{i+1}. [{title}]({url})\n"
    
    # 3. 发送
    if has_data:
        send_feishu(msg)
        print("🎉 推送完成！请查看飞书！")
    else:
        print("⚠️ 两个接口都挂了，请稍后再试。")

if __name__ == "__main__":
    main()
