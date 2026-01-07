import requests
import json
import re
from datetime import datetime
from xml.etree import ElementTree

# ==================== 👇 配置区域 👇 ====================
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/f241b8ab-434f-48f4-997c-5d8437a3f9e1"
TOP_N = 2  # 每个平台只取前2条，防止内容过长
# ========================================================

def get_headers():
    return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}

def fetch_content(url):
    """利用 Jina Reader 提取正文 (黑科技)"""
    if not url or "javascript" in url: return ""
    try:
        # 加上 r.jina.ai 前缀，自动提取正文
        resp = requests.get(f"https://r.jina.ai/{url}", timeout=15)
        if resp.status_code == 200:
            text = resp.text
            # 简单清洗 markdown 图片链接，只保留文字
            text = re.sub(r'!\[.*?\]\(.*?\)', '', text) 
            return text[:800].replace('\n', ' ') + "..." # 截取前800字
    except Exception:
        pass
    return "（正文获取超时，建议根据标题搜索）"

# 1. 36氪 (最适合写公众号的素材)
def get_36kr():
    print("🔍 抓取36氪...")
    data = []
    try:
        url = "https://36kr.com/feed"
        resp = requests.get(url, headers=get_headers(), timeout=10)
        root = ElementTree.fromstring(resp.content)
        channel = root.find('channel')
        for item in channel.findall('item')[:TOP_N]:
            title = item.find('title').text
            link = item.find('link').text
            content = fetch_content(link) # 36氪必须抓正文
            data.append({"title": title, "url": link, "content": content})
    except Exception as e:
        print(f"❌ 36氪出错: {e}")
    return data

# 2. 知乎热榜 (优化版)
def get_zhihu():
    print("🔍 抓取知乎...")
    data = []
    try:
        url = "https://api.zhihu.com/topstory/hot-list"
        resp = requests.get(url, headers=get_headers(), timeout=10)
        items = resp.json().get('data', [])
        for item in items[:TOP_N]:
            target = item.get('target', {})
            title = target.get('title', '无标题')
            link = target.get('url', '').replace('api.zhihu.com/questions', 'www.zhihu.com/question')
            # 知乎如果抓不到正文，就只看标题
            content = fetch_content(link) 
            data.append({"title": title, "url": link, "content": content if len(content)>50 else "（建议点击链接查看讨论）"})
    except Exception as e:
        print(f"❌ 知乎出错: {e}")
    return data

# 3. 百度热搜 (修复乱码 Bug)
def get_baidu():
    print("🔍 抓取百度...")
    data = []
    try:
        url = "https://top.baidu.com/board?tab=realtime"
        resp = requests.get(url, headers=get_headers(), timeout=10)
        # 修复：优化正则，精准提取标题，不再包含 appUrl 乱码
        # 寻找 "word":"内容", 这样的结构
        titles = re.findall(r'"word":"(.*?)"', resp.text)
        
        for t in titles[:TOP_N]:
            # 百度大部分是政治/社会新闻，我们标记一下让 AI 注意过滤
            data.append({
                "title": t, 
                "url": f"https://www.baidu.com/s?wd={t}", 
                "content": "【注意】百度多为社会/时政新闻，请AI在写作时严格过滤敏感话题。"
            })
    except Exception as e:
        print(f"❌ 百度出错: {e}")
    return data

def send_feishu(all_data):
    print("🚀 发送中...")
    full_text = "📅 **公众号爆款素材库**\n请复制下方内容，发送给 AI 助手进行写作：\n\n"
    
    for source, items in all_data.items():
        if not items: continue
        full_text += f"【{source}】\n{'='*20}\n"
        for item in items:
            full_text += f"📌 标题：{item['title']}\n"
            full_text += f"🔗 链接：{item['url']}\n"
            full_text += f"📝 素材摘要：\n{item['content']}\n\n"
            
    headers = {'Content-Type': 'application/json'}
    payload = {"msg_type": "text", "content": {"text": full_text}}
    try:
        requests.post(WEBHOOK_URL, headers=headers, data=json.dumps(payload))
        print("🎉 发送成功")
    except Exception as e:
        print(f"发送报错: {e}")

if __name__ == "__main__":
    final_data = {}
    final_data["36氪科技"] = get_36kr() # 放在第一个，因为质量最高
    final_data["知乎热榜"] = get_zhihu()
    final_data["百度热搜"] = get_baidu()
    send_feishu(final_data)
