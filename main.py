import requests
import json
import re
from datetime import datetime

# ==================== 👇 配置区域 👇 ====================
# 你的飞书 Webhook 地址 (保持不变)
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/f241b8ab-434f-48f4-997c-5d8437a3f9e1"

# 纯净阅读前缀 (这是把网页转成纯文字的黑科技)
# 点击链接后，会通过 Jina AI 自动提取正文，不显示原网页广告
READ_API = "https://r.jina.ai/"
# ========================================================

def get_headers():
    """伪装成手机浏览器 (获取移动端数据通常更全)"""
    return {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'Accept': 'application/json, text/plain, */*'
    }

def clean_link(url):
    """将链接转换为纯净阅读模式"""
    return f"{READ_API}{url}"

# ========== 1. 百度热搜 (爬虫) ==========
def scrape_baidu():
    print("🔍 正在抓取百度...")
    data = []
    try:
        url = "https://top.baidu.com/board?tab=realtime"
        # 百度比较特殊，需要用电脑 UA
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
        resp = requests.get(url, headers=headers, timeout=10)
        content = resp.text
        # 正则提取
        titles = re.findall(r'"word":"(.*?)",', content)
        # 百度热度值通常在 desc 附近，这里简化，直接按顺序（百度默认就是按热度排的）
        for t in titles[:10]:
            if t:
                data.append({
                    "title": t,
                    "url": clean_link(f"https://www.baidu.com/s?wd={t}"),
                    "heat": "Top" # 百度网页版很难正则出准确热度数字
                })
        print(f"✅ 百度: {len(data)} 条")
    except Exception as e:
        print(f"❌ 百度失败: {e}")
    return data

# ========== 2. 微博热搜 (爬虫) ==========
def scrape_weibo():
    print("🔍 正在抓取微博...")
    data = []
    try:
        url = "https://s.weibo.com/top/summary"
        headers = {'Cookie': 'SUB=1'} # 微博必填
        resp = requests.get(url, headers=headers, timeout=10)
        html = resp.text
        # 正则提取: href, 标题, 热度
        # 格式: <a href="/weibo?q=...">标题</a> ... <span>123456</span>
        pattern = re.compile(r'<a href="(/weibo\?q=[^"]+)" target="_blank">([^<]+)</a>.*?<span>(\d+)</span>', re.S)
        matches = pattern.findall(html)
        
        for m in matches[:10]:
            data.append({
                "title": m[1],
                "url": clean_link(f"https://s.weibo.com{m[0]}"),
                "heat": f"{int(m[2])/10000:.1f}w" # 换算成万
            })
        print(f"✅ 微博: {len(data)} 条")
    except Exception as e:
        print(f"❌ 微博失败: {e}")
    return data

# ========== 3. 知乎热榜 (API) ==========
def scrape_zhihu():
    print("🔍 正在抓取知乎...")
    data = []
    try:
        # 知乎官方接口 (比网页爬虫稳定)
        url = "https://api.zhihu.com/topstory/hot-list"
        resp = requests.get(url, headers=get_headers(), timeout=10)
        res_json = resp.json()
        
        items = res_json.get('data', [])
        for item in items[:10]:
            target = item.get('target', {})
            title = target.get('title')
            link = target.get('url', '').replace('api.zhihu.com/questions', 'www.zhihu.com/question')
            heat_val = item.get('detail_text', '').replace(' 热度', '')
            
            if title and link:
                data.append({
                    "title": title,
                    "url": clean_link(link),
                    "heat": heat_val
                })
        print(f"✅ 知乎: {len(data)} 条")
    except Exception as e:
        print(f"❌ 知乎失败: {e}")
    return data

# ========== 4. 今日头条 (聚合API) ==========
def scrape_toutiao():
    print("🔍 正在抓取头条...")
    data = []
    try:
        # 头条反爬最变态，直接抓网页必死。
        # 这里使用一个稳定的聚合源，如果这个挂了，脚本不会崩，只会跳过头条
        url = "https://api.oioweb.cn/api/common/toutiao/hotSearch"
        resp = requests.get(url, headers=get_headers(), timeout=15)
        res_json = resp.json()
        
        if res_json.get('code') == 200:
            items = res_json.get('result', [])
            for item in items[:10]:
                title = item.get('word')
                # 头条没有直接链接，通常是搜索链接
                link = f"https://so.toutiao.com/search?keyword={title}"
                heat = item.get('hot_value', 'Top')
                
                data.append({
                    "title": title,
                    "url": clean_link(link),
                    "heat": heat
                })
            print(f"✅ 头条: {len(data)} 条")
    except Exception as e:
        print(f"❌ 头条失败: {e}")
    return data

# ========== 发送逻辑 ==========
def send_feishu(wb_data, bd_data, zh_data, tt_data):
    # 构建卡片内容
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 定义一个小函数来生成板块
    def make_section(title, icon, data_list):
        if not data_list: return ""
        text = f"\n{icon} **{title}**\n"
        for i, item in enumerate(data_list):
            # 格式: 1. 标题 (热度)
            # 链接已经全部被替换为 Jina Reader 链接
            heat_str = f" 🔥{item['heat']}" if item.get('heat') else ""
            text += f"{i+1}. [{item['title']}]({item['url']}){heat_str}\n"
        return text

    content = f"📅 **{today} 全网爆款选题表**\n> 点击标题可直接查看纯净文字版"
    content += make_section("微博热搜", "🔴", wb_data)
    content += make_section("知乎热榜", "🔵", zh_data)
    content += make_section("百度热搜", "🟢", bd_data)
    content += make_section("今日头条", "🟠", tt_data)

    headers = {'Content-Type': 'application/json'}
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "template": "blue",
                "title": {"content": "🔥 爆款选题挖掘机 (纯净阅读版)", "tag": "plain_text"}
            },
            "elements": [
                {"tag": "div", "text": {"content": content, "tag": "lark_md"}},
                {
                    "tag": "note", 
                    "elements": [{"content": "提示: 链接已通过 AI 转为纯文本，加载速度极快", "tag": "plain_text"}]
                }
            ]
        }
    }
    
    try:
        requests.post(WEBHOOK_URL, headers=headers, data=json.dumps(payload))
        print("🎉 发送成功！")
    except Exception as e:
        print(f"发送飞书失败: {e}")

def main():
    print("🚀 任务启动...")
    
    # 并行抓取 (其实是串行，但很快)
    wb = scrape_weibo()
    bd = scrape_baidu()
    zh = scrape_zhihu()
    tt = scrape_toutiao()
    
    # 只要有一个源有数据，就发送
    if wb or bd or zh or tt:
        send_feishu(wb, bd, zh, tt)
    else:
        print("⚠️ 全军覆没，所有接口都拿不到数据，请检查网络或IP。")

if __name__ == "__main__":
    main()
