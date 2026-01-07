import requests
import json
import re
import time
from datetime import datetime
from xml.etree import ElementTree

# ==================== 👇 配置区域 👇 ====================
# 你的飞书 Webhook 地址
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/f241b8ab-434f-48f4-997c-5d8437a3f9e1"

# 每个平台抓取数量 (建议 2-3 条，否则飞书发不出)
TOP_N = 2
# ========================================================

def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    }

def fetch_content(url):
    """利用 Jina Reader 提取正文"""
    if not url or "javascript" in url: return "无效链接"
    try:
        # 加上 r.jina.ai 前缀
        resp = requests.get(f"https://r.jina.ai/{url}", timeout=15)
        if resp.status_code == 200:
            text = resp.text
            # 截取前 600 字作为素材
            return text[:600].replace('\n', ' ') + "..."
    except Exception:
        pass
    return "（正文抓取超时，请参考标题）"

# 1. 知乎热榜 (官方接口)
def get_zhihu():
    print("🔍 正在抓取知乎...")
    data = []
    try:
        # 直接访问知乎官方接口，不走第三方代理
        url = "https://api.zhihu.com/topstory/hot-list"
        resp = requests.get(url, headers=get_headers(), timeout=10)
        items = resp.json().get('data', [])
        
        for item in items[:TOP_N]:
            target = item.get('target', {})
            title = target.get('title', '无标题')
            # 替换为网页链接
            link = target.get('url', '').replace('api.zhihu.com/questions', 'www.zhihu.com/question')
            print(f"   读取: {title[:10]}...")
            content = fetch_content(link)
            data.append({"title": title, "url": link, "content": content})
    except Exception as e:
        print(f"❌ 知乎出错: {e}")
    return data

# 2. 百度热搜 (原生爬虫)
def get_baidu():
    print("🔍 正在抓取百度...")
    data = []
    try:
        url = "https://top.baidu.com/board?tab=realtime"
        resp = requests.get(url, headers=get_headers(), timeout=10)
        # 正则提取标题
        titles = re.findall(r'"word":"(.*?)",', resp.text)
        
        for t in titles[:TOP_N]:
            # 百度正文太杂，为了稳定性，我们构造搜索链接，并让 AI 直接针对标题写作
            link = f"https://www.baidu.com/s?wd={t}"
            print(f"   读取: {t[:10]}...")
            # 百度不抓正文，防止脚本被封 IP，直接返回提示
            data.append({
                "title": t, 
                "url": link, 
                "content": "此为实时社会热点，请直接基于标题搜索写作。"
            })
    except Exception as e:
        print(f"❌ 百度出错: {e}")
    return data

# 3. 36氪 (RSS 订阅源)
def get_36kr():
    print("🔍 正在抓取36氪...")
    data = []
    try:
        url = "https://36kr.com/feed"
        resp = requests.get(url, headers=get_headers(), timeout=10)
        root = ElementTree.fromstring(resp.content)
        channel = root.find('channel')
        
        count = 0
        for item in channel.findall('item'):
            if count >= TOP_N: break
            title = item.find('title').text
            link = item.find('link').text
            print(f"   读取: {title[:10]}...")
            content = fetch_content(link)
            data.append({"title": title, "url": link, "content": content})
            count += 1
    except Exception as e:
        print(f"❌ 36氪出错: {e}")
    return data

def send_feishu(all_data):
    print("🚀 正在发送...")
    
    # 标题必须包含 "热搜"，否则会被飞书拦截！
    full_text = "📅 **全网热搜选题素材库**\n"
    full_text += "可以直接复制下方内容喂给 AI：\n\n"
    
    has_data = False
    for source, items in all_data.items():
        if not items: continue
        has_data = True
        full_text += f"【{source}】\n{'='*20}\n"
        for item in items:
            full_text += f"📌 标题：{item['title']}\n"
            full_text += f"🔗 链接：{item['url']}\n"
            full_text += f"📝 摘要：{item['content']}\n\n"
            
    if not has_data:
        print("❌ 没有任何数据，取消发送")
        return

    headers = {'Content-Type': 'application/json'}
    # 使用 text 类型发送长文本
    payload = {
        "msg_type": "text",
        "content": {
            "text": full_text
        }
    }
    
    try:
        r = requests.post(WEBHOOK_URL, headers=headers, data=json.dumps(payload))
        print(f"发送结果: {r.status_code} {r.text}")
    except Exception as e:
        print(f"发送报错: {e}")

def main():
    final_data = {}
    final_data["知乎热榜"] = get_zhihu()
    final_data["36氪科技"] = get_36kr()
    final_data["百度热搜"] = get_baidu()
    
    send_feishu(final_data)

if __name__ == "__main__":
    main()
