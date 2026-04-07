"""
股票操作建议推送脚本 v3.0
1. 持仓股票做T建议
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

# 持仓股票（做T专用）
HOLDINGS = {
    "国机精工": "002046",
    "臻镭科技": "688270",
    "国博电子": "688375",
    "拓维信息": "002261",
    "超捷股份": "301005",
    "信维通信": "300136",
    "斯瑞新材": "688102",
}

# 激进资金
AGGRESSIVE_CAPITAL = 30000  # 3万

def get_stock_price(code):
    """获取股票实时价格"""
    try:
        market = "sh" if code.startswith("6") else "sz"
        url = f"https://qt.gtimg.cn/q={market}{code}"
        resp = requests.get(url, timeout=10)
        resp.encoding = 'gbk'
        data = resp.text
        parts = data.split('~')

        if len(parts) > 32:
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
                "amplitude": round(float(parts[33]) - float(parts[5]), 2)
            }
    except Exception as e:
        print(f"获取 {code} 数据失败: {e}")
    return None

def analyze_holding_t(code, name, data):
    """持仓做T策略分析"""
    if not data:
        return f"[{name}] 数据获取失败"

    price = data["price"]
    open_p = data["open"]
    high = data["high"]
    low = data["low"]
    change_pct = data["change_pct"]
    amplitude = data["amplitude"]

    # 做T核心：判断是应该先卖后买，还是先买后卖
    # 早盘判断方向，午盘/尾盘执行

    if change_pct > 5:
        # 大涨：先卖后买
        sell_price = price
        buy_price = round(price * 0.98, 2)  # 回落2%买回
        action = "[T] 做空卖出"
        strategy = f"冲高{change_pct}%，建议卖出部分，{buy_price}以下买回"
        t_action = "先卖后买"
    elif change_pct > 2:
        # 上涨：持有或少量做T
        action = "[>] 持有+小T"
        strategy = f"上涨{change_pct}%，可高位卖1/4，回调买回"
        t_action = "先卖后买"
    elif change_pct > -2:
        # 震荡：观望或不做
        action = "[~] 观望"
        strategy = f"横盘{change_pct}%，方向不明，观望为主"
        t_action = "观望"
    elif change_pct > -5:
        # 下跌：考虑接回或加仓
        action = "[T] 做多接回"
        strategy = f"回调{change_pct}%，若低位可少量接回做T"
        t_action = "先买后卖"
    else:
        # 大跌：止损或观望
        action = "[!] 注意止损"
        strategy = f"暴跌{change_pct}%，检查是否破位，谨慎操作"
        t_action = "谨慎"

    return f"""[{data['name']} ({code})]
现价: {price} | 涨跌: {change_pct:+.2f}% | 振幅: {amplitude:.2f}%
今日最高: {high} | 今日最低: {low}
操作: {action} | 策略: {strategy}"""

def analyze_aggressive_fund(stocks_data, report_type):
    """3万激进资金建议"""
    opportunities = []

    # 找出今天表现最强的持仓股
    strong_stocks = [(k, v, d) for k, v, d in stocks_data if d and d["change_pct"] > 2]
    weak_stocks = [(k, v, d) for k, v, d in stocks_data if d and d["change_pct"] < -2]

    result = []

    if report_type == "早盘":
        # 早盘：判断今日方向，给出布局建议
        result.append("【3万激进资金 - 早盘布局】")
        result.append("-" * 30)

        if strong_stocks:
            result.append(f"强势股：{', '.join([s[0] for s in strong_stocks])}")
            result.append("建议：可追入最强势的那只1/3仓位")

        if weak_stocks:
            result.append(f"弱势股：{', '.join([s[0] for s in weak_stocks])}")
            result.append("建议：避免弱势股，不抄底")

        result.append("")
        result.append("早盘策略：")
        result.append("1. 观察开盘30分钟内方向")
        result.append("2. 强势股回调2%以内可追")
        result.append("3. 止损线：-3%必须出")

    elif report_type == "午盘":
        # 午盘：根据上午走势给下午建议
        result.append("【3万激进资金 - 午盘策略】")
        result.append("-" * 30)

        result.append("下午操作要点：")
        result.append("1. 上午已涨5%+的不追，等尾盘")
        result.append("2. 上午跌3%+的可以轻仓抄底博反弹")
        result.append("3. 重点关注：超跌+缩量的标的")

        if weak_stocks:
            stock = weak_stocks[0]
            result.append(f"")
            result.append(f"激进机会：{stock[0]}({stock[1]})")
            result.append(f"现价{stock[2]['price']}，下跌{stock[2]['change_pct']}%")
            result.append(f"建议：可考虑1万试探性买入")

    else:  # 收盘
        # 收盘：总结今天+布局明天
        result.append("【3万激进资金 - 收盘复盘】")
        result.append("-" * 30)

        # 排序涨跌
        sorted_stocks = sorted(stocks_data, key=lambda x: x[2]["change_pct"] if x[2] else 0, reverse=True)

        result.append("今日持仓排名：")
        for i, (name, code, data) in enumerate(sorted_stocks[:3], 1):
            if data:
                result.append(f"{i}. {name}: {data['change_pct']:+.2f}%")

        result.append("")
        result.append("明日激进方向：")
        result.append("1. 选今日跌幅大但缩量的")
        result.append("2. 选板块轮动中率先反弹的")
        result.append("3. 开盘30分钟不追，等方向明确")

    return "\n".join(result)

def generate_report(report_type="早盘"):
    """生成完整报告"""
    now = datetime.now()
    title = f"[Stock] {report_type}建议 | {now.strftime('%m月%d日 %H:%M')}"

    content = []
    content.append("=" * 55)
    content.append(f"【{report_type}股票操作建议】")
    content.append("=" * 55)

    # 获取所有持仓数据
    stocks_data = []
    for name, code in HOLDINGS.items():
        data = get_stock_price(code)
        stocks_data.append((name, code, data))
        time.sleep(0.5)

    # ===== 持仓做T建议 =====
    content.append("")
    content.append("━" * 25)
    content.append("【持仓做T建议】(不换仓位，高卖低买)")
    content.append("━" * 25)

    for name, code, data in stocks_data:
        analysis = analyze_holding_t(code, name, data)
        content.append(analysis)
        content.append("-" * 25)

    # ===== 激进资金建议 =====
    content.append("")
    content.append("━" * 25)
    content.append("【3万激进资金建议】(激进追涨杀跌)")
    content.append("━" * 25)

    aggressive = analyze_aggressive_fund(stocks_data, report_type)
    content.append(aggressive)

    content.append("")
    content.append("-" * 55)
    content.append("[免责声明] 激进策略风险极高，请量力而行！")
    content.append(f"生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")

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

    print("-" * 55)
    print(content)
    print("-" * 55)

    print("正在发送推送...")
    send_message(title, content)

if __name__ == "__main__":
    main()
