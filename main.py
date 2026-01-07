import requests
import json
import time

# ==================== 👇 配置区域 👇 ====================
# 你的飞书 Webhook 地址
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/f241b8ab-434f-48f4-997c-5d8437a3f9e1"

# 每个平台抓取前几名？(建议不要超过 3 个，否则内容太长飞书发不出去)
TOP_N = 3 
# ========================================================

def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    }

def fetch_full_content(url):
    """
    核心黑科技：调用 Jina Reader 自动把网页转成纯文字
    """
    try:
        # 加上 r.jina.ai 前缀，它会自动去除广告提取正文
        api_url = f"https://r.jina.ai/{url}"
        resp = requests.get(api_url, timeout=15)
        if resp.status_code == 200:
            # 拿到纯净的 Markdown 文本
            text = resp.text
            # 简单清洗：如果文章太长，截取前 1000 字（防止飞书报错）
            # 如果你需要喂给大模型，1000-2000字是比较合理的
            return text[:2000] + "\n...(内容过长已截断)..." if len(text) > 2000 else text
    except Exception:
        return "⚠️ 正文抓取失败"
    return "⚠️ 正文为空"

# ========== 1. 知乎热榜 (高质量问答) ==========
def get_zhihu():
    print("🔍 正在抓取知乎...")
    data = []
    try:
        url = "https://api.oioweb.cn/api/common/zhihu/hotSearch"
        resp = requests.get(url, headers=get_headers(), timeout=10)
        items = resp.json().get('result', [])
        
        for item in items[:TOP_N]:
            title = item.get('title')
            # 拼接知乎链接
            link = f"https://www.zhihu.com/question/{item.get('id')}"
            print(f"   正在读取正文: {title}...")
            content = fetch_full_content(link)
            data.append({"title": title, "url": link, "content": content})
    except Exception as e:
        print(f"❌ 知乎失败: {e}")
    return data

# ========== 2. 百度热搜 (社会热点) ==========
def get_baidu():
    print("🔍 正在抓取百度...")
    data = []
    try:
        url = "https://api.oioweb.cn/api/common/baidu/hotSearch"
        resp = requests.get(url, headers=get_headers(), timeout=10)
        items = resp.json().get('result', [])
        
        for item in items[:TOP_N]:
            title = item.get('word')
            # 百度热搜本身没有固定正文链接，我们用百度搜索的第一条作为参考，或者直接用百科
            # 这里为了稳定性，我们构造一个搜索链接
            link = f"https://www.baidu.com/s?wd={title}"
            # 百度搜索页很难提取正文，这里我们只保留标题，
            # 或者尝试抓取该词条的百度百科（如果有）
            # *修正*：为了给大模型素材，我们尝试抓取该热点关联的第一条新闻（模拟）
            # 由于百度反爬严重，这里我们只保留【标题+简介】，不强行抓正文，防止脚本卡死
            data.append({"title": title, "url": link, "content": "（百度热搜为实时聚合，建议直接使用标题询问 AI）"})
    except Exception as e:
        print(f"❌ 百度失败: {e}")
    return data

# ========== 3. 36氪 (科技/商业/AI - 强烈推荐) ==========
def get_36kr():
    print("🔍 正在抓取36氪(科技)...")
    data = []
    try:
        # 36氪的官方 RSS 源，非常稳定
        url = "https://36kr.com/feed"
        resp = requests.get(url, headers=get_headers(), timeout=10)
        # 简单解析 XML
        from xml.etree import ElementTree
        root = ElementTree.fromstring(resp.content)
        channel = root.find('channel')
        
        count = 0
        for item in channel.findall('item'):
            if count >= TOP_N: break
            title = item.find('title').text
            link = item.find('link').text
            print(f"   正在读取正文: {title}...")
            content = fetch_full_content(link)
            data.append({"title": title, "url": link, "content": content})
            count += 1
    except Exception as e:
        print(f"❌ 36氪失败: {e}")
    return data

def send_feishu_long_text(all_data):
    """
    因为内容很长，我们不能用卡片（Card），只能用富文本（Post）
    """
    print("🚀 正在发送给飞书...")
    
    # 拼接一个超级长的 Prompt
    full_text = "📅 **今日选题素材库 (已提取正文)**\n"
    full_text += "请复制以下内容发送给 AI (ChatGPT/DeepSeek) 进行改写：\n\n"
    
    for source_name, items in all_data.items():
        if not items: continue
        full_text += f"【{source_name}】\n"
        full_text += "------------------------------\n"
        for item in items:
            full_text += f"标题：{item['title']}\n"
            full_text += f"链接：{item['url']}\n"
            full_text += f"正文摘要：\n{item['content']}\n"
            full_text += "------------------------------\n\n"

    # 飞书文本消息最大支持约 30k 字符，我们分段发送或者直接发一个长文本
    headers = {'Content-Type': 'application/json'}
    payload = {
        "msg_type": "text",
        "content": {
            "text": full_text
        }
    }
    
    try:
        # 如果太长，截断发送
        if len(full_text) > 30000:
            payload['content']['text'] = full_text[:30000] + "\n...(剩余内容过长已省略)"
            
        requests.post(WEBHOOK_URL, headers=headers, data=json.dumps(payload))
        print("🎉 发送成功！")
    except Exception as e:
        print(f"发送失败: {e}")

def main():
    print("🚀 任务启动...")
    
    final_data = {}
    
    # 1. 获取知乎 (含正文)
    final_data["知乎热榜"] = get_zhihu()
    
    # 2. 获取36氪 (含正文 - 适合科技公众号)
    final_data["36氪科技"] = get_36kr()
    
    # 3. 获取百度 (仅标题，作补充)
    final_data["百度热搜"] = get_baidu()
    
    # 发送
    send_feishu_long_text(final_data)

if __name__ == "__main__":
    main()
