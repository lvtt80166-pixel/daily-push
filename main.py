import requests
import json
import re
from datetime import datetime

# ==================== 👇 配置区域 👇 ====================
# 你的飞书 Webhook 地址 (已填好)
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/f241b8ab-434f-48f4-997c-5d8437a3f9e1"
# ========================================================

def get_headers():
    """伪装成最新的 Chrome 浏览器"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cookie': 'SUB=1' # 微博有时候需要一个假 Cookie
    }

def scrape_baidu():
    """方案1：抓取百度热搜 (最稳定，作为保底)"""
    print("🔍 正在抓取百度热搜...")
    try:
        url = "https://top.baidu.com/board?tab=realtime"
        resp = requests.get(url, headers=get_headers(), timeout=15)
        if resp.status_code == 200:
            # 使用正则提取 JSON 数据
            content = resp.text
            # 简单粗暴正则匹配标题
            titles = re.findall(r'"word":"(.*?)",', content)
            # 匹配 URL (百度 URL 比较复杂，这里简化处理，直接跳搜索页)
            if titles:
                # 百度返回的数据前几个通常是置顶，取前1-11
                data = []
                for t in titles[:11]:
                    if t:
                        data.append({
                            "title": t,
                            "url": f"https://www.baidu.com/s?wd={t}"
                        })
                print(f"✅ 百度获取成功: {len(data)} 条")
                return data
    except Exception as e:
        print(f"❌ 百度失败: {e}")
    return []

def scrape_weibo():
    """方案2：暴力抓取微博网页版 (非API)"""
    print("🔍 正在抓取微博网页...")
    try:
        url = "https://s.weibo.com/top/summary"
        resp = requests.get(url, headers=get_headers(), timeout=15)
        if resp.status_code == 200:
            html = resp.text
            # 正则提取 <a href="/weibo?q=...">标题</a>
            # 排除置顶的（置顶的通常没有 rank）
            pattern = r'<a href="(/weibo\?q=[^"]+)" target="_blank">([^<]+)</a>'
            matches = re.findall(pattern, html)
            
            data = []
            for m in matches[:11]: # 取前11个
                link = "https://s.weibo.com" + m[0]
                title = m[1]
                if "javascript" not in link:
                    data.append({"title": title, "url": link})
            
            if data:
                print(f"✅ 微博网页获取成功: {len(data)} 条")
                return data
            else:
                print("⚠️ 微博网页内容为空，可能需要验证码")
        else:
            print(f"❌ 微博网页返回: {resp.status_code}")
    except Exception as e:
        print(f"❌ 微博抓取报错: {e}")
    return []

def send_feishu(content):
    headers = {'Content-Type': 'application/json'}
    data = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "template": "blue",
                "title": {"content": "🔥 今日全网热搜 (爬虫版)", "tag": "plain_text"}
            },
            "elements": [
                {"tag": "div", "text": {"content": content, "tag": "lark_md"}},
                {"tag": "note", "elements": [{"content": "数据来源: 实时网页抓取", "tag": "plain_text"}]}
            ]
        }
    }
    try:
        requests.post(WEBHOOK_URL, headers=headers, data=json.dumps(data))
    except Exception as e:
        print(f"发送飞书失败: {e}")

def main():
    print("🚀 启动强力爬虫模式...")
    
    # 1. 抓取
    weibo_list = scrape_weibo()
    baidu_list = scrape_baidu() # 用百度替代不稳定的知乎
    
    # 2. 拼装文案
    today = datetime.now().strftime("%Y-%m-%d")
    msg = f"📅 **{today}**\n"
    
    has_data = False
    
    if weibo_list:
        has_data = True
        msg += f"\n🔴 **微博热搜 (实时)**\n"
        for i, item in enumerate(weibo_list):
            msg += f"{i+1}. [{item['title']}]({item['url']})\n"
            
    if baidu_list:
        has_data = True
        # 如果微博挂了，百度就是主力
        msg += f"\n🔵 **百度热搜 (稳定)**\n"
        for i, item in enumerate(baidu_list):
            msg += f"{i+1}. [{item['title']}]({item['url']})\n"
    
    # 3. 发送
    if has_data:
        send_feishu(msg)
        print("🎉 推送完成！请查看飞书！")
    else:
        # 如果连百度都挂了，那是真断网了
        print("⚠️ 全网抓取失败，GitHub 网络可能异常。")

if __name__ == "__main__":
    main()
