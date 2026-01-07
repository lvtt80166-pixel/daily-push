import requests
import json
import re
import time
from datetime import datetime

# ==================== 👇 配置区域 👇 ====================
# 你的飞书 Webhook 地址
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/f241b8ab-434f-48f4-997c-5d8437a3f9e1"

# 每个平台只取前 2 名 (为了防止飞书消息过长发不出去)
# 如果觉得不够，可以改成 3
TOP_N = 2
# ========================================================

def get_headers_mobile():
    """伪装成手机，获取数据更全"""
    return {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
    }

def get_headers_pc():
    """伪装成电脑"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    }

def fetch_full_content(url):
    """
    调用 Jina Reader 提取正文
    """
    if not url or "javascript" in url: return "无效链接"
    try:
        # 使用 jina 读取器
        api_url = f"https://r.jina.ai/{url}"
        resp = requests.get(api_url, timeout=20)
        if resp.status_code == 200:
            text = resp.text
            # 截取前 800 字，避免飞书报错
            if len(text) > 800:
                return text[:800] + "\n...(篇幅过长，建议复制链接给AI)..."
            return text
    except Exception:
        pass
    return "⚠️ 正文抓取超时，请直接参考标题"

# ========== 1. 知乎热榜 (官方接口 - 稳) ==========
def get_zhihu():
    print("🔍 正在抓取知乎...")
    data = []
    try:
        url = "https://api.zhihu.com/topstory/hot-list"
        resp = requests.get(url, headers=get_headers_mobile(), timeout=10)
        items = resp.json().get('data', [])
        
        for item in items[:TOP_N]:
            target = item.get('target', {})
            title = target.get('title')
            # 构造知乎问题链接
            link = target.get('url', '').replace('api.zhihu.com/questions', 'www.zhihu.com/question')
            
            print(f"   正在读取: {title[:10]}...")
            content = fetch_full_content(link)
            data.append({"title": title, "url": link, "content": content})
    except Exception as e:
        print(f"❌ 知乎失败: {e}")
    return data

# ========== 2. 百度热搜 (原生爬虫 - 稳) ==========
def get_baidu():
    print("🔍 正在抓取百度...")
    data = []
    try:
        url = "https://top.baidu.com/board?tab=realtime"
        resp = requests.get(url, headers=get_headers_pc(), timeout=10)
        content = resp.text
        # 正则提取标题
        titles = re.findall(r'"word":"(.*?)",', content)
        
        for t in titles[:TOP_N]:
            # 百度链接比较特殊，我们直接用搜索链接
            link = f"https://www.baidu.com/s?wd={t}"
            print(f"   正在读取: {t[:10]}...")
            # 百度搜索页内容太杂，我们只让 AI 读标题即可，
            # 或者尝试读取搜索结果的第一段文字，这里为了稳定性，
            # 我们直接返回提示，因为百度热搜通常标题就是内容。
            data.append({
                "title": t, 
                "url": link, 
                "content": "（百度热点为实时事件，请直接将标题发送给AI进行搜索）"
            })
    except Exception as e:
        print(f"❌ 百度失败: {e}")
    return data

# ========== 3. 36氪 (RSS - 稳) ==========
def get_36kr():
    print("🔍 正在抓取36氪...")
    data = []
    try:
        url = "https://36kr.com/feed"
        resp = requests.get(url, headers=get_headers_pc(), timeout=10)
        from xml.etree import ElementTree
        root = ElementTree.fromstring(resp.content)
        channel = root.find('channel')
        
        count = 0
        for item in channel.findall('item'):
            if count >= TOP_N: break
            title = item.find('title').text
            link = item.find('link').text
            print(f"   正在读取: {title[:10]}...")
            content = fetch_full_content(link)
            data.append({"title": title, "url": link, "content": content})
            count += 1
    except Exception as e:
