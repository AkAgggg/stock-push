"""
股票操作建议推送脚本 v5.0 - 通俗易懂版
1. 持仓股操作建议（简单明了）
2. 3万激进资金操作建议
"""

import requests
from datetime import datetime
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ============ 配置区 ============
SEND_KEY = "SCT334455TmE1WOH5QWyW2WU61yptgszVi"

# 持仓股票
HOLDINGS = {
    "国机精工": "002046",
    "臻镭科技": "688270",
    "国博电子": "688375",
    "拓维信息": "002261",
    "超捷股份": "301005",
    "信维通信": "300136",
    "斯瑞新材": "688102",
}

def get_stock_price(code):
    """获取股票实时价格"""
    try:
        market = "sh" if code.startswith("6") else "sz"
        url = f"https://qt.gtimg.cn/q={market}{code}"
        resp = requests.get(url, timeout=10)
        resp.encoding = 'gbk'
        data = resp.text
        parts = data.split('~')

        if len(parts) > 34:
            return {
                "name": parts[1],
                "price": float(parts[3]),
                "yesterday_close": float(parts[4]),
                "open": float(parts[5]),
                "high": float(parts[33]),
                "low": float(parts[34]) if parts[34] else float(parts[3]),
                "volume": float(parts[6]) / 10000,
                "change": round(float(parts[3]) - float(parts[4]), 2),
                "change_pct": round((float(parts[3]) - float(parts[4])) / float(parts[4]) * 100, 2),
                "amplitude": round((float(parts[33]) - float(parts[5])) if parts[33] else 0, 2),
                "turnover": float(parts[38]) if len(parts) > 38 else 0,
            }
    except Exception as e:
        print(f"获取 {code} 数据失败: {e}")
    return None

def analyze_holding(code, name, data):
    """持仓分析 - 简单明了版本"""
    if not data:
        return f"【{name}】数据获取失败"

    price = data["price"]
    change_pct = data["change_pct"]
    high = data["high"]
    low = data["low"]

    # ===== 大白话判断 =====
    
    if change_pct > 6:
        # 大涨 >6%
        action = "🔴 大涨！可以卖一半"
        detail = f"涨了{change_pct:.1f}%，高价卖掉一半\n跌回{round(price*0.97, 2)}以下再买回来"
        emoji = "🔥🔥"
        advice = "卖！"
        
    elif change_pct > 3:
        # 上涨 3-6%
        action = "🟠 小涨，可以卖点"
        detail = f"涨了{change_pct:.1f}%，可以卖1/4\n回调{round(price*0.98, 2)}以下买回"
        emoji = "🔥"
        advice = "可卖"
        
    elif change_pct > 0:
        # 小涨 0-3%
        action = "🟡 小涨，不动"
        detail = f"涨了{change_pct:.1f}%，太小了，不动"
        emoji = "📊"
        advice = "观望"
        
    elif change_pct > -3:
        # 小跌 0~-3%
        action = "🔵 小跌，观望"
        detail = f"跌了{change_pct:.1f}%，还不到买的时候"
        emoji = "📉"
        advice = "等更低"
        
    elif change_pct > -6:
        # 下跌 -3%~-6%
        action = "🟣 下跌，可以买"
        detail = f"跌了{change_pct:.1f}%，可以考虑买一点\n涨回{round(price*1.02, 2)}以上就卖"
        emoji = "💎"
        advice = "可买"
        
    else:
        # 大跌 >-6%
        action = "🔴 大跌！注意！"
        detail = f"暴跌{change_pct:.1f}%，小心！\n如果继续跌破{round(price*0.97, 2)}要考虑止损"
        emoji = "⚠️⚠️"
        advice = "止损"

    # 计算当日最大盈利/亏损
    if data["open"] and data["open"] > 0:
        if data["open"] < price:
            profit = round((price - data["open"]) / data["open"] * 100, 1)
            profit_info = f"📈 买在最低可赚 {profit}%"
        else:
            loss = round((data["open"] - price) / data["open"] * 100, 1)
            profit_info = f"📉 买在最高亏 {loss}%"
    else:
        profit_info = ""

    return f"""【{name}】{emoji}
━━━━━━━━━━━━━━━━
💰 现价: {price}元
📊 涨跌: {change_pct:+.1f}%  ({'上涨' if change_pct > 0 else '下跌'})
📐 今日区间: {low} ~ {high}

🎯 操作建议: {action}
💡 {detail}

{profit_info}

━━━━━━━━━━━━━━━"""

def analyze_aggressive_fund(stocks_data, report_type):
    """3万激进资金建议"""
    sorted_stocks = sorted(stocks_data, key=lambda x: x[2]["change_pct"] if x[2] else 0, reverse=True)
    
    result = []

    if report_type == "早盘":
        result.append("━━━━━━━━━━━━━━━━━━━━")
        result.append("【3万激进资金 - 早盘计划】")
        result.append("━━━━━━━━━━━━━━━━━━━━")
        result.append("")
        
        result.append("📋 今日操作计划：")
        result.append("")
        
        # 找强势股
        up_stocks = [(k, v, d) for k, v, d in sorted_stocks if d and d["change_pct"] > 2]
        down_stocks = [(k, v, d) for k, v, d in sorted_stocks if d and d["change_pct"] < -2]
        
        if up_stocks:
            result.append("✅ 【可以买】")
            for name, code, data in up_stocks[:2]:
                buy_price = round(data["price"] * 0.99, 2)
                stop_price = round(data["price"] * 0.97, 2)
                shares = int(10000 / data["price"])
                result.append(f"  • {name}({code})")
                result.append(f"    现价:{data['price']} 涨:{data['change_pct']:+.1f}%")
                result.append(f"    建议买价:{buy_price} 止损:{stop_price}")
                result.append(f"    可买:{shares}股 ≈ {shares*data['price']:.0f}元")
                result.append("")
        
        if down_stocks:
            result.append("❌ 【不要买】")
            for name, code, data in down_stocks[:2]:
                result.append(f"  • {name}({code}) 跌:{data['change_pct']:.1f}% 危险！")
        
        result.append("━━━━━━━━━━━━━━━━━━━━")
        result.append("📌 操作规则：")
        result.append("1. 每只最多买1万")
        result.append("2. 亏3%必须卖！")
        result.append("3. 涨5%可以卖一半")
        result.append("4. 早盘30分钟不追高")

    elif report_type == "午盘":
        result.append("━━━━━━━━━━━━━━━━━━━━")
        result.append("【3万激进资金 - 午盘策略】")
        result.append("━━━━━━━━━━━━━━━━━━━━")
        result.append("")
        
        result.append("📋 下午重点关注：")
        
        # 找跌幅大的
        down_stocks = [(k, v, d) for k, v, d in sorted_stocks if d and d["change_pct"] < -3]
        
        if down_stocks:
            result.append("")
            result.append("💎 【超跌机会】")
            for name, code, data in down_stocks[:1]:
                result.append(f"  {name}({code})")
                result.append(f"  现价:{data['price']} 跌:{data['change_pct']:.1f}%")
                if data["change_pct"] < -5:
                    result.append("  ⚠️ 超跌！可以轻仓买1/3")
                    shares = int(10000 / 3 / data["price"])
                    result.append(f"  建议买:{shares}股 ≈ {shares*data['price']:.0f}元")
        
        result.append("")
        result.append("📌 下午规则：")
        result.append("• 上午涨5%+的不要追")
        result.append("• 跌3%+可轻仓买")
        result.append("• 收盘前30分钟决定")

    else:  # 收盘
        result.append("━━━━━━━━━━━━━━━━━━━━")
        result.append("【3万激进资金 - 收盘复盘】")
        result.append("━━━━━━━━━━━━━━━━━━━━")
        result.append("")
        
        result.append("📊 今日涨跌排行：")
        for i, (name, code, data) in enumerate(sorted_stocks, 1):
            if data:
                arrow = "🔴" if data["change_pct"] > 0 else "🟢"
                result.append(f"  {i}. {arrow} {name}: {data['change_pct']:+.1f}%")
        
        # 计算总收益
        total = sum([d["change_pct"] for _, _, d in sorted_stocks if d])
        result.append("")
        if total > 0:
            result.append(f"📈 今日总收益: +{total:.1f}%")
        else:
            result.append(f"📉 今日总收益: {total:.1f}%")
        
        result.append("")
        result.append("📋 明日计划：")
        result.append("• 选今日跌但没暴跌的")
        result.append("• 开盘30分钟不要买")
        result.append("• 等方向明确再动手")
        result.append("")
        result.append("⚠️ 止损纪律：亏3%必须卖！")

    return "\n".join(result)

def generate_report(report_type="早盘"):
    """生成完整报告"""
    now = datetime.now()
    title = f"[股票] {report_type}建议 | {now.strftime('%m月%d日 %H:%M')}"

    content = []
    content.append("━━━━━━━━━━━━━━━━━━━━")
    content.append(f"  【{report_type}股票操作建议】")
    content.append(f"  时间: {now.strftime('%H:%M')}")
    content.append("━━━━━━━━━━━━━━━━━━━━")

    # 获取所有持仓数据
    stocks_data = []
    print(f"正在获取 {len(HOLDINGS)} 只股票数据...")
    for name, code in HOLDINGS.items():
        data = get_stock_price(code)
        stocks_data.append((name, code, data))
        time.sleep(0.3)

    # ===== 持仓操作建议 =====
    content.append("")
    content.append("━━━━━━━━━━━━━━━━━━━━")
    content.append("【持仓股操作建议】")
    content.append("━━━━━━━━━━━━━━━━━━━━")
    content.append("")

    for name, code, data in stocks_data:
        analysis = analyze_holding(code, name, data)
        content.append(analysis)

    # ===== 激进资金建议 =====
    content.append("")
    content.append("━━━━━━━━━━━━━━━━━━━━")
    content.append("【3万激进资金计划】")
    content.append("━━━━━━━━━━━━━━━━━━━━")
    content.append("")

    aggressive = analyze_aggressive_fund(stocks_data, report_type)
    content.append(aggressive)

    content.append("")
    content.append("━━━━━━━━━━━━━━━━━━━━")
    content.append("⚠️ 免责声明：本建议仅供参考，股市有风险！")
    content.append(f"生成: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    return title, "\n".join(content)

def send_message(title, content):
    """发送推送"""
    try:
        url = f"https://sctapi.ftqq.com/{SEND_KEY}.send"
        resp = requests.post(url, data={"title": title, "desp": content}, timeout=10)
        result = resp.json()

        if result.get("code") == 0 or result.get("data", {}).get("error") == "SUCCESS":
            print("[OK] 推送成功!")
            return True
        else:
            print(f"[X] 推送失败: {result}")
            return False
    except Exception as e:
        print(f"[X] 推送异常: {e}")
        return False

def main():
    report_type = sys.argv[1] if len(sys.argv) > 1 else "早盘"

    print(f"正在生成 {report_type} 股票分析报告...")

    title, content = generate_report(report_type)

    print("-" * 40)
    print(content)
    print("-" * 40)

    print("正在发送推送...")
    send_message(title, content)

if __name__ == "__main__":
    main()
