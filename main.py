import requests
import json
from datetime import datetime

# ==================== 👇 配置区域 👇 ====================
# 你的飞书 Webhook 地址 (已填好)
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/f241b8ab-434f-48f4-997c-5d8437a3f9e1"
# ========================================================

def get_data_with_fallback(source_name):
    """
    三保险抓取逻辑：
    Plan A: Oioweb API (稳定)
    Plan B: Vvhan API (备用)
    Plan C: TenAPI (兜底)
    """
    
    # 定义三个数据源的地址
    sources = [
        {
            "id": "A",
            "name": "Oioweb (0号源)",
            "weibo": "https://api.oioweb.cn/api/common/weibo/hotSearch",
            "zhihu": "https://api.oioweb.cn/api/common/zhihu/hotSearch",
            "data_field": "result"  # 这个接口的数据在 'result' 字段里
        },
        {
            "id": "B",
            "name": "Vvhan (韩小韩)",
            "weibo": "https://api.vvhan.com/api/hotlist/wbHot",
            "zhihu": "https://api.vvhan.com/api/hotlist/zhihuHot",
            "data_field": "data"    # 这个接口的数据在 'data' 字段里
        },
        {
            "id": "C",
            "name": "TenAPI (腾讯源)",
            "weibo": "https://tenapi.cn/v2/weibohot",
            "zhihu": "https://tenapi.cn/v2/zhihuhot",
            "data_field": "data"
        }
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # === 开始尝试 ===
    if source_name == "weibo":
        print("🔍 正在抓取微博热搜...")
    else:
        print("🔍 正在抓取知乎热榜...")

    for plan in sources:
        url = plan[source_name] # 获取对应源的 URL
        try:
            print(f"   Trying Plan {plan['id']}: {plan['name']} ...")
            resp = requests.get(url, headers=headers, timeout=15)
            
            if resp.status_code == 200:
                res_json = resp.json()
                # 尝试提取数据
                data_list = res_json.get(plan['data_field'])
                
                # 如果没拿到，可能是接口格式变了，尝试通用字段 'list'
                if not data_list:
                    data_list = res_json.get('list')

                if data_list and isinstance(data_list, list) and len(data_list) > 0:
                    print(f"   ✅ Plan {plan['id']} 成功！获取到 {len(data_list)} 条数据")
                    return data_list[:10], plan['name'] # 返回数据和源的名字
                else:
                    print(f"   ❌ Plan {plan['id']} 返回了 200 但没数据，尝试下一个...")
            else:
                print(f"   ❌ Plan {plan['id']} 网络请求失败: {resp.status_code}")
                
        except Exception as e:
            print(f"   ❌ Plan {plan['id']} 报错: {e}")
            continue # 报错了就试下一个

    print(f"⚠️ {source_name} 所有方案全军覆没，请检查网络。")
    return [], "未知来源"

def send_feishu(content):
    headers = {'Content-Type': 'application/json'}
    data = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "template": "blue",
                "title": {"content": "🔥 今日全网热搜 (多源版)", "tag": "plain_text"}
            },
            "elements": [
                {"tag": "div", "text": {"content": content, "tag": "lark_md"}},
                {"tag": "note", "elements": [{"content": "数据来源: 聚合多线路API", "tag": "plain_text"}]}
            ]
        }
    }
    try:
        requests.post(WEBHOOK_URL, headers=headers, data=json.dumps(data))
    except Exception as e:
        print(f"发送飞书失败: {e}")

def main():
    print("🚀 任务启动！")
    
    # 1. 抓取 (带自动重试)
    weibo_list, wb_source = get_data_with_fallback("weibo")
    zhihu_list, zh_source = get_data_with_fallback("zhihu")
    
    # 2. 拼装文案
    today = datetime.now().strftime("%Y-%m-%d")
    msg = f"📅 **{today}**\n"
    
    has_data = False
    
    if weibo_list:
        has_data = True
        msg += f"\n🔴 **微博热搜 Top10** (源:{wb_source})\n"
        for i, item in enumerate(weibo_list):
            title = item.get('title', item.get('name', '无标题')).strip()
            # 处理不同接口 URL 字段不一样的情况
            url = item.get('url', item.get('link', '#'))
            hot = item.get('hot', item.get('hot_value', ''))
            msg += f"{i+1}. [{title}]({url}) `{hot}`\n"
            
    if zhihu_list:
        has_data = True
        msg += f"\n🔵 **知乎热榜 Top10** (源:{zh_source})\n"
        for i, item in enumerate(zhihu_list):
            title = item.get('title', '无标题').strip()
            url = item.get('url', item.get('link', '#'))
            msg += f"{i+1}. [{title}]({url})\n"
    
    # 3. 发送
    if has_data:
        send_feishu(msg)
        print("🎉 推送完成！这次肯定响！")
    else:
        print("⚠️ 灾难性故障：所有备用线路都挂了，请稍后再试。")

if __name__ == "__main__":
    main()
