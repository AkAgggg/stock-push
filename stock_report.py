"""
股票操作建议推送脚本 v4.0 - 升级版
1. 持仓股票做T建议 + 技术指标
2. 3万激进资金智能选股策略
3. 追涨杀跌激进模式
"""

import requests
from datetime import datetime
import time
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ============ 配置区 ============
# 从环境变量获取SENDKEY（GitHub Actions需要）
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
AGGRESSIVE_STOP_LOSS = 0.03  # 止损线 -3%

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
                "turnover": float(parts[38]) if len(parts) > 38 else 0,  # 换手率
                "market_cap": float(parts[44]) / 100000000 if len(parts) > 44 and parts[44] else 0,  # 市值亿
            }
    except Exception as e:
        print(f"获取 {code} 数据失败: {e}")
    return None

def get_kline_data(code, days=5):
    """获取K线数据用于技术分析"""
    try:
        # 使用东方财富API获取K线
        market = "1" if code.startswith("6") else "0"
        url = f"http://push2his.eastmoney.com/api/qt/stock/kline/get?secid={market}.{code}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&lmt={days}&end=20500101"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        if data.get("data") and data["data"].get("klines"):
            klines = data["data"]["klines"]
            result = []
            for kline in klines:
                parts = kline.split(',')
                if len(parts) >= 6:
                    result.append({
                        "date": parts[0],
                        "open": float(parts[1]),
                        "close": float(parts[2]),
                        "high": float(parts[3]),
                        "low": float(parts[4]),
                        "volume": float(parts[5]),
                    })
            return result
    except Exception as e:
        print(f"获取K线 {code} 失败: {e}")
    return None

def calculate_ma(klines, period=5):
    """计算移动平均线"""
    if len(klines) < period:
        return None
    prices = [k["close"] for k in klines[-period:]]
    return round(sum(prices) / period, 2)

def calculate_volatility(klines):
    """计算波动率"""
    if len(klines) < 2:
        return 0
    closes = [k["close"] for k in klines]
    avg = sum(closes) / len(closes)
    variance = sum((c - avg) ** 2 for c in closes) / len(closes)
    return round((variance ** 0.5) / avg * 100, 2)

def analyze_technical(code, name, data, klines):
    """技术指标分析"""
    if not data:
        return {}
    
    result = {
        "ma5": None,
        "ma10": None,
        "volatility": 0,
        "trend": "震荡",  # 上涨/下跌/震荡
        "signal": "观望",  # 买入/卖出/观望
        "score": 50,  # 强势评分 0-100
    }
    
    if klines and len(klines) >= 2:
        # 计算MA
        if len(klines) >= 5:
            result["ma5"] = calculate_ma(klines, 5)
        if len(klines) >= 10:
            result["ma10"] = calculate_ma(klines, 10)
        
        # 计算波动率
        result["volatility"] = calculate_volatility(klines[-5:]) if len(klines) >= 5 else 0
        
        # 判断趋势
        if len(klines) >= 3:
            recent_closes = [k["close"] for k in klines[-3:]]
            if all(recent_closes[i] > recent_closes[i-1] for i in range(1, len(recent_closes))):
                result["trend"] = "上涨"
            elif all(recent_closes[i] < recent_closes[i-1] for i in range(1, len(recent_closes))):
                result["trend"] = "下跌"
        
        # 计算强势评分
        score = 50
        score += data["change_pct"] * 2  # 涨跌贡献
        score += (data["amplitude"] - 2) * 3 if data["amplitude"] > 2 else 0  # 振幅贡献
        
        # MA多头排列加分
        if result["ma5"] and result["ma10"] and data["price"] > result["ma5"] > result["ma10"]:
            score += 15
        elif result["ma5"] and data["price"] > result["ma5"]:
            score += 8
        
        # 换手率加分（活跃）
        if data["turnover"] > 5:
            score += 5
        
        result["score"] = max(0, min(100, round(score)))
        
        # 生成信号
        if result["score"] >= 75 and data["change_pct"] > 3:
            result["signal"] = "强势买入"
        elif result["score"] >= 65 and data["change_pct"] > 2:
            result["signal"] = "关注"
        elif result["score"] < 35:
            result["signal"] = "回避"
        elif result["trend"] == "下跌" and data["change_pct"] < -3:
            result["signal"] = "超跌反弹"
    
    return result

def analyze_holding_t(code, name, data, klines=None):
    """持仓做T策略分析"""
    if not data:
        return f"[{name}] 数据获取失败"

    price = data["price"]
    open_p = data["open"]
    high = data["high"]
    low = data["low"]
    change_pct = data["change_pct"]
    amplitude = data["amplitude"]
    
    # 技术分析
    tech = analyze_technical(code, name, data, klines)

    # 做T核心策略
    if change_pct > 6:
        action = "[T+降仓]"
        strategy = f"冲高{change_pct}%，建议卖出1/3，{round(price*0.97,2)}以下买回"
        t_action = "先卖后买"
        priority = "★★★★★"
    elif change_pct > 3:
        action = "[T卖]"
        strategy = f"上涨{change_pct}%，可卖1/4，回调买回"
        t_action = "先卖后买"
        priority = "★★★★☆"
    elif change_pct > 0:
        action = "[持有]"
        strategy = f"小涨{change_pct}%，持有待涨"
        t_action = "观望"
        priority = "★★★☆☆"
    elif change_pct > -3:
        action = "[观望]"
        strategy = f"小跌{change_pct}%，方向不明"
        t_action = "观望"
        priority = "★★☆☆☆"
    elif change_pct > -6:
        action = "[T接]"
        strategy = f"回调{change_pct}%，低位可接回"
        t_action = "先买后卖"
        priority = "★★★☆☆"
    else:
        action = "[!止损]"
        strategy = f"暴跌{change_pct}%，检查是否破位！"
        t_action = "谨慎"
        priority = "★★★★★"

    # 添加技术信号
    tech_info = ""
    if tech["signal"] != "观望":
        tech_info = f"\n技术信号: {tech['signal']} | 评分: {tech['score']} | 趋势: {tech['trend']}"
        if tech["ma5"]:
            tech_info += f" | MA5: {tech['ma5']}"

    return f"""【{data['name']}】{priority}
现价: {price} | 涨跌: {change_pct:+.2f}% | 振幅: {amplitude:.2f}%
最高: {high} | 最低: {low} | 换手: {data['turnover']:.1f}%
操作: {action} | {strategy}{tech_info}"""

def get_hot_stocks():
    """获取热门概念股（激进选股）"""
    try:
        # 东方财富涨幅榜
        url = "http://push2.eastmoney.com/api/qt/clist/get?cb=jQuery&pn=1&pz=20&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23,m:1+t:A,m:0+t:7,m:1+t:3,m:0+t:10,m:1+t:11&fields=f2,f3,f4,f12,f14,f9,f10&_=1"
        resp = requests.get(url, timeout=10)
        text = resp.text
        # 解析JSON
        start = text.find('(') + 1
        end = text.rfind(')')
        if start > 0 and end > start:
            data = json.loads(text[start:end])
            if data.get("data") and data["data"].get("diff"):
                stocks = []
                for item in data["data"]["diff"][:10]:
                    if item.get("f3", 0) > 5:  # 涨幅>5%
                        stocks.append({
                            "code": item.get("f12", ""),
                            "name": item.get("f14", ""),
                            "price": item.get("f2", 0),
                            "change_pct": item.get("f3", 0),
                            "volume": item.get("f10", 0),
                        })
                return stocks
    except Exception as e:
        print(f"获取热门股失败: {e}")
    return []

def analyze_aggressive_fund(stocks_data, report_type):
    """3万激进资金建议"""
    opportunities = []

    # 排序涨跌
    sorted_stocks = sorted(stocks_data, key=lambda x: x[2]["change_pct"] if x[2] else 0, reverse=True)
    
    # 找出强势和弱势股
    strong_stocks = [(k, v, d) for k, v, d in sorted_stocks if d and d["change_pct"] > 2]
    weak_stocks = [(k, v, d) for k, v, d in sorted_stocks if d and d["change_pct"] < -2]

    result = []

    if report_type == "早盘":
        result.append("【3万激进资金 - 早盘布局】")
        result.append("=" * 30)
        result.append("")
        
        # 今日强势标的
        result.append("【今日强势股】（追涨首选）")
        for i, (name, code, data) in enumerate(sorted_stocks[:3], 1):
            if data and data["change_pct"] > 0:
                buy_price = round(data["price"] * 0.99, 2)
                stop_loss = round(data["price"] * 0.97, 2)
                result.append(f"{i}. {name}({code})")
                result.append(f"   现价:{data['price']} 涨幅:{data['change_pct']:+.2f}%")
                result.append(f"   建议买入价: {buy_price} | 止损: {stop_loss}")
                result.append(f"   可买入: {int(10000/data['price'])}股 ≈ {int(10000/data['price'])*data['price']:.0f}元")
        
        result.append("")
        result.append("【操作纪律】")
        result.append("1. 仓位分配: 每只最多1万，单只止损-3%")
        result.append("2. 早盘30分钟不追，等方向明确")
        result.append("3. 冲高回落不追，宁可错过")
        
        # 弱势提醒
        if weak_stocks:
            result.append("")
            result.append("【回避标的】（杀跌风险）")
            for name, code, data in weak_stocks[:2]:
                result.append(f"✗ {name}({code}) 下跌{data['change_pct']:.2f}%")

    elif report_type == "午盘":
        result.append("【3万激进资金 - 午盘策略】")
        result.append("=" * 30)
        result.append("")
        
        result.append("【下午重点关注】")
        if strong_stocks:
            top = strong_stocks[0]
            result.append(f"最强势: {top[0]}({top[1]}) 涨幅{top[2]['change_pct']:.2f}%")
            result.append("策略: 若保持强势到尾盘，可收盘前买入")
        
        result.append("")
        result.append("【午盘操作要点】")
        result.append("1. 上午已涨5%+ → 不追，等尾盘")
        result.append("2. 上午跌3%+ → 可轻仓1/3试探")
        result.append("3. 重点: 超跌+缩量 = 反弹信号")
        
        if weak_stocks:
            stock = weak_stocks[0]
            result.append("")
            result.append(f"【激进机会】{stock[0]}({stock[1]})")
            result.append(f"现价:{stock[2]['price']} 下跌:{stock[2]['change_pct']:.2f}%")
            # 检查是否超跌
            if stock[2]["change_pct"] < -5:
                result.append("⚠️ 超跌信号！可考虑1/3仓位入场")
                result.append(f"买入数量: {int(10000/stock[2]['price'])}股")

    else:  # 收盘
        result.append("【3万激进资金 - 收盘复盘】")
        result.append("=" * 30)
        result.append("")
        
        # 今日总结
        result.append("【今日持仓排名】")
        for i, (name, code, data) in enumerate(sorted_stocks, 1):
            if data:
                emoji = "🔴" if data["change_pct"] > 0 else "🟢"
                result.append(f"{i}. {emoji} {name}: {data['change_pct']:+.2f}%")
        
        result.append("")
        result.append("【明日激进方向】")
        result.append("1. 选今日强势+缩量回调的")
        result.append("2. 选板块轮动中率先反弹的")
        result.append("3. 开盘30分钟不追，等方向")
        result.append("4. 止损线: -3%必须出！")
        
        # 计算今日盈亏
        total_change = sum([d["change_pct"] for _, _, d in sorted_stocks if d])
        if total_change > 0:
            result.append("")
            result.append(f"【今日总收益】+{total_change:.2f}%")
        else:
            result.append("")
            result.append(f"【今日总收益】{total_change:.2f}%")

    return "\n".join(result)

def generate_report(report_type="早盘"):
    """生成完整报告"""
    now = datetime.now()
    title = f"[Stock] {report_type}建议 | {now.strftime('%m月%d日 %H:%M')}"

    content = []
    content.append("=" * 55)
    content.append(f"【{report_type}股票操作建议】")
    content.append(f"时间: {now.strftime('%Y-%m-%d %H:%M')}")
    content.append("=" * 55)

    # 获取所有持仓数据
    stocks_data = []
    print(f"正在获取 {len(HOLDINGS)} 只持仓股数据...")
    for name, code in HOLDINGS.items():
        data = get_stock_price(code)
        klines = get_kline_data(code)
        stocks_data.append((name, code, data, klines))
        time.sleep(0.3)

    # ===== 持仓做T建议 =====
    content.append("")
    content.append("━" * 25)
    content.append("【持仓做T建议】")
    content.append("━" * 25)

    for name, code, data, klines in stocks_data:
        analysis = analyze_holding_t(code, name, data, klines)
        content.append(analysis)
        content.append("-" * 25)

    # ===== 激进资金建议 =====
    content.append("")
    content.append("━" * 25)
    content.append("【3万激进资金建议】")
    content.append("━" * 25)

    # 转换为旧格式供激进分析函数使用
    old_format_data = [(n, c, d) for n, c, d, _ in stocks_data]
    aggressive = analyze_aggressive_fund(old_format_data, report_type)
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
