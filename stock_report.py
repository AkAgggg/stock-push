"""
股票操作建议推送脚本 v9.0 - 全市场扫描版
核心：激进资金从全市场找标的，不只局限于持仓股
"""

import requests
from datetime import datetime, timedelta
import time
import sys
import io
import json
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 导入智能系统
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from backtest_system import BacktestSystem
    from smart_engine import SmartStockEngine
    from market_scanner import MarketScanner
    HAS_SMART = True
    HAS_SCANNER = True
except Exception as e:
    print(f"导入智能模块失败: {e}")
    HAS_SMART = False
    HAS_SCANNER = False

# ============ 配置 ============
SEND_KEY = "SCT334455TmE1WOH5QWyW2WU61yptgszVi"

# 激进资金
AGGRESSIVE_MONEY = 30000

# 初始化系统
backtest = BacktestSystem() if HAS_SMART else None
smart_engine = SmartStockEngine() if HAS_SMART else None
market_scanner = MarketScanner() if HAS_SCANNER else None

# 当前推荐的股票（用于追踪）
current_recommendations = []

def record_recommendation(name, code, data, action, reason, report_type):
    """记录推荐到回测系统"""
    global current_recommendations
    if not backtest or not data:
        return None
    
    rec_id = backtest.add_recommendation(
        stock_code=code,
        stock_name=name,
        recommend_price=data["price"],
        current_change=data["change_pct"],
        strategy=f"{action}|{report_type}",
        signal_type=action,
        target_date=datetime.now().strftime("%Y-%m-%d")
    )
    
    rec = {
        "id": rec_id,
        "name": name,
        "code": code,
        "price": data["price"],
        "action": action,
        "reason": reason,
        "report_type": report_type
    }
    current_recommendations.append(rec)
    return rec_id

def get_strategy_advice():
    """获取基于回测的策略建议"""
    if not backtest:
        return None
    
    optimized = backtest.get_optimized_strategy()
    
    if "error" in optimized or optimized.get("total_samples", 0) < 5:
        return None
    
    suggestions = optimized.get("suggestions", [])
    if not suggestions:
        return None
    
    advice = []
    advice.append("")
    advice.append("━━━━━━━━━━━━━━━━━━━━━━━")
    advice.append("📊 【历史回测优化建议】")
    advice.append("━━━━━━━━━━━━━━━━━━━━━━━")
    advice.append("")
    
    for s in suggestions[:2]:
        advice.append(f"◆ {s['finding']}")
        advice.append(f"  → {s['action']}")
        advice.append("")
    
    advice.append(f"📈 当前胜率: {optimized.get('win_rate', 0)}%")
    advice.append(f"💰 平均收益: {optimized.get('avg_profit', 0)}%")
    advice.append("━━━━━━━━━━━━━━━━━━━━━━━")
    
    return "\n".join(advice)


def track_recommendations():
    """追踪之前推荐的股票表现"""
    if not backtest:
        return
    
    # 获取待追踪的记录
    pending = [r for r in backtest.recommendations if r["status"] == "pending"]
    
    if not pending:
        return
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    for rec in pending:
        # 计算推荐过去了多少天
        rec_date = datetime.strptime(rec.get("date", ""), "%Y-%m-%d")
        days_passed = (datetime.now() - rec_date).days
        
        code = rec["stock_code"]
        data = get_stock_price(code)
        
        if not data:
            continue
        
        current_price = data["price"]
        buy_price = rec.get("buy_price", current_price)
        
        if days_passed >= 1 and not rec.get("result_1d"):
            change = (current_price - buy_price) / buy_price * 100
            backtest.update_result(rec["id"], "1d", current_price, change)
        
        if days_passed >= 3 and not rec.get("result_3d"):
            change = (current_price - buy_price) / buy_price * 100
            backtest.update_result(rec["id"], "3d", current_price, change)
        
        if days_passed >= 5 and not rec.get("result_5d"):
            change = (current_price - buy_price) / buy_price * 100
            backtest.update_result(rec["id"], "5d", current_price, change)

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

# 激进资金
AGGRESSIVE_MONEY = 30000

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
                "high": float(parts[33]) if parts[33] else 0,
                "low": float(parts[34]) if parts[34] else 0,
                "change_pct": round((float(parts[3]) - float(parts[4])) / float(parts[4]) * 100, 2),
                "volume": float(parts[6]) / 10000,
                "turnover": float(parts[38]) if len(parts) > 38 and parts[38] else 0,
            }
    except Exception as e:
        print(f"获取 {code} 数据失败: {e}")
    return None

def analyze_holding(code, name, data):
    """持仓分析"""
    if not data:
        return f"【{name}】数据获取失败"

    price = data["price"]
    change_pct = data["change_pct"]

    # ===== 操作建议 =====
    if change_pct > 6:
        action = "🔴 大涨！可以卖一半"
        detail = f"涨了{change_pct:.1f}%，高价卖掉一半\n跌回{round(price*0.97, 2)}以下再买回来"
    elif change_pct > 3:
        action = "🟠 小涨，可以卖点"
        detail = f"涨了{change_pct:.1f}%，可以卖1/4\n回调{round(price*0.98, 2)}以下买回"
    elif change_pct > 0:
        action = "🟡 小涨，不动"
        detail = f"涨了{change_pct:.1f}%，太小了，不动"
    elif change_pct > -3:
        action = "🔵 小跌，观望"
        detail = f"跌了{change_pct:.1f}%，还不到买的时候"
    elif change_pct > -6:
        action = "🟣 下跌，可以买"
        detail = f"跌了{change_pct:.1f}%，可以考虑买一点\n涨回{round(price*1.02, 2)}以上就卖"
    else:
        action = "🔴 大跌！注意！"
        detail = f"暴跌{change_pct:.1f}%，小心！\n如果继续跌破{round(price*0.97, 2)}要考虑止损"

    return f"""【{name}】{price}元 {change_pct:+.1f}%
→ {action}
  {detail}"""

def analyze_aggressive_fund(stocks_data, report_type):
    """3万激进资金 - 全市场扫描版
    
    不只分析持仓股，而是从全市场找最合适的激进标的
    """
    result = []
    sorted_stocks = sorted(stocks_data, key=lambda x: x[2]["change_pct"] if x[2] else 0, reverse=True)
    
    # ========== 分析市场环境 ==========
    market = "震荡"
    if smart_engine:
        valid_data = [d for _, _, d in stocks_data if d]
        market = smart_engine.analyze_market(valid_data)
    
    market_desc = {
        "强势": "行情好，积极操作",
        "弱势": "行情差，谨慎操作",
        "震荡": "行情一般，见机行事",
        "平稳": "波动小，少操作"
    }
    
    # ========== 早盘：全市场扫描找标的 ==========
    if report_type == "早盘":
        result.append(f"📊 市场: {market}市 | {market_desc.get(market, '')}")
        
        # 使用全市场扫描器
        if market_scanner:
            print("[激进资金] 开始全市场扫描...")
            market_targets = market_scanner.scan_aggressive_targets(market)
            
            if market_targets:
                result.append("")
                result.append("🔥 全市场激进标的:")
                
                # 生成推荐
                if smart_engine:
                    recs = smart_engine.generate_recommendation_from_market(market_targets, limit=2)
                else:
                    recs = []
                
                for i, target in enumerate(market_targets[:3], 1):
                    change = target.get("change_pct", 0)
                    price = target.get("price", 0)
                    name = target.get("name", "未知")
                    code = target.get("code", "")
                    strategy = target.get("strategy", "未知")
                    reason = target.get("reason", "")
                    amplitude = target.get("amplitude", 0)
                    
                    if price <= 0:
                        continue
                    
                    # 计算建议
                    if change > 9.5:
                        action = "⚠️ 不追"
                        detail = "接近涨停，等明天"
                        shares = 0
                    elif change > 6:
                        action = "🟠 轻仓试"
                        detail_shares = int(3000 / price)
                        shares = detail_shares
                        detail = f"建议{shares}股"
                    elif change > 0:
                        action = "✅ 可以买"
                        shares = int(10000 / price)
                        detail = f"建议{shares}股"
                    elif change > -3:
                        action = "🔵 观望"
                        shares = 0
                        detail = "等跌更多再买"
                    elif change > -6:
                        action = "🟣 超跌买"
                        shares = int(10000 / price)
                        detail = f"建议{shares}股抢反弹"
                    else:
                        action = "🔴 大跌注意"
                        shares = int(5000 / price)
                        detail = f"建议{shares}股，止损严"
                    
                    result.append("")
                    result.append(f"#{i} {name}({code})")
                    result.append(f"   现价:{price} 涨幅:{change:+.1f}% 振幅:{amplitude:.1f}%")
                    result.append(f"   策略:{strategy} | {reason}")
                    result.append(f"   → {action} {detail}")
                    
                    # 计算止损和目标价
                    if price > 0:
                        buy_price = round(price * 0.998, 2) if change > 0 else round(price * 0.99, 2)
                        stop_loss = round(buy_price * 0.97, 2)
                        target_price = round(buy_price * 1.05, 2)
                        result.append(f"   买价:{buy_price} 止损:{stop_loss} 目标:{target_price}")
                    
                    # 记录到回测系统
                    if backtest and shares > 0:
                        target["price"] = price
                        target["change_pct"] = change
                        record_recommendation(name, code, target, strategy, reason, "早盘")
            else:
                result.append("")
                result.append("❌ 今日市场无明显机会，观望为主")
        else:
            result.append("❌ 扫描器未加载，使用持仓股分析")
        
        result.append("")
        result.append("📌 规则: 亏3%必须止损 | 最多买2只各1万")
        result.append("━━━━━━━━━━━━━━━━━━━━━━━")
        result.append("📌 早盘规则:")
        result.append("1. 每只最多买1万，总共最多3万")
        result.append("2. 亏3%必须止损！不要犹豫")
        result.append("3. 涨5%以上可以卖一半")
        result.append("4. 开盘30分钟不要追高")

    elif report_type == "午盘":
        result.append("━━━━━━━━━━━━━━━━━━━━━━━")
        result.append("【3万激进资金 - 午盘策略】")
        result.append("━━━━━━━━━━━━━━━━━━━━━━━")
        
        # 更新市场判断
        if smart_engine:
            market = smart_engine.market_status or market
        
        result.append("")
        result.append(f"📊 当前市场: {market}市")
        
        # 午盘再扫一次全市场，看盘中机会
        if market_scanner:
            print("[激进资金] 午盘全市场扫描...")
            market_targets = market_scanner.scan_aggressive_targets(market)
            
            # 找强势机会
            up_targets = [t for t in market_targets if t.get("change_pct", 0) > 2]
            down_targets = [t for t in market_targets if t.get("change_pct", 0) < -3]
            
            if up_targets:
                result.append("")
                result.append("📈 强势机会:")
                for t in up_targets[:1]:
                    change = t.get("change_pct", 0)
                    if change > 5:
                        result.append(f"  {t.get('name')} 涨{change:.1f}% → 不追，等回调")
                    else:
                        result.append(f"  {t.get('name')} 涨{change:.1f}% → 可尾盘轻仓")
            
            if down_targets:
                result.append("")
                result.append("💎 超跌机会:")
                for t in down_targets[:1]:
                    change = t.get("change_pct", 0)
                    if change < -5:
                        shares = int(10000 / t.get("price", 0)) if t.get("price", 0) > 0 else 0
                        result.append(f"  {t.get('name')} 跌{change:.1f}% → 可买入")
                        result.append(f"    建议{shares}股 | 止损{round(t.get('price', 0)*0.97, 2)}")
                    else:
                        result.append(f"  {t.get('name')} 跌{change:.1f}% → 跌不够多，等")
            elif not up_targets:
                result.append("📊 走势平稳，无特别机会")
        else:
            # 回退到持仓股分析
            down_stocks = [(k, v, d) for k, v, d in sorted_stocks if d and d["change_pct"] < -3]
            up_stocks = [(k, v, d) for k, v, d in sorted_stocks if d and d["change_pct"] > 3]
            
            if up_stocks:
                result.append("")
                result.append("📈 上午强势股:")
                for name, code, data in up_stocks[:1]:
                    if data["change_pct"] > 5:
                        result.append(f"  {name} 涨{data['change_pct']:+.1f}% → 不要追，等回调")
                    else:
                        result.append(f"  {name} 涨{data['change_pct']:+.1f}% → 可尾盘轻仓")
            
            if down_stocks:
                result.append("")
                result.append("💎 超跌机会:")
                for name, code, data in down_stocks[:1]:
                    if data["change_pct"] < -5:
                        shares = int(10000 / 3 / data["price"])
                        result.append(f"  {name} 跌{data['change_pct']:.1f}% → 可买1/3仓")
                        result.append(f"    建议买{shares}股 | 止损{round(data['price']*0.97, 2)}元")
                        record_recommendation(name, code, data, "超跌反弹", f"跌幅{data['change_pct']:.1f}%", "午盘")
                    else:
                        result.append(f"  {name} 跌{data['change_pct']:.1f}% → 跌不够多，等")

        result.append("")
        result.append("📌 午盘规则: 涨5%+不追 | 跌3%+轻仓试 | 收盘前30分定")

    else:  # 收盘
        result.append("━━━━━━━━━━━━━━━━━━━━━━━")
        result.append("【3万激进资金 - 收盘总结】")
        result.append("━━━━━━━━━━━━━━━━━━━━━━━")
        
        # 今日涨跌
        result.append("")
        result.append("📊 今日涨跌:")
        for i, (name, code, data) in enumerate(sorted_stocks[:5], 1):
            if data:
                arrow = "🔴" if data["change_pct"] > 0 else "🟢"
                result.append(f"  {i}. {arrow} {name}: {data['change_pct']:+.1f}%")
        
        total = sum([d["change_pct"] for _, _, d in sorted_stocks if d])
        if total > 0:
            result.append(f"→ 整体上涨 {total:.1f}%")
        elif total < 0:
            result.append(f"→ 整体下跌 {abs(total):.1f}%")
        
        # 午盘全市场扫描结果（如果有的话，留给明天参考）
        if market_scanner and market:
            print("[激进资金] 收盘全市场扫描，为明天做准备...")
            market_targets = market_scanner.scan_aggressive_targets(market)
            
            if market_targets:
                result.append("")
                result.append("🌙 明日关注标的:")
                for i, t in enumerate(market_targets[:2], 1):
                    change = t.get("change_pct", 0)
                    result.append(f"  #{i} {t.get('name')}({t.get('code')}) 今日{change:+.1f}%")
                    result.append(f"     策略:{t.get('strategy', '')} | {t.get('reason', '')}")
        
        # 明日计划
        best = sorted_stocks[0] if sorted_stocks else None
        if best and best[2]:
            if best[2]["change_pct"] > 0:
                result.append(f"★ 明日重点: {best[0]} (今日涨{best[2]['change_pct']:.1f}%)")
            elif best[2]["change_pct"] > -3:
                result.append(f"★ 明日关注: {best[0]} (今日跌{best[2]['change_pct']:.1f}%)")
        
        result.append("")
        result.append("⚠️ 核心纪律: 亏3%必须卖！不扛单！")
        
        # 回测统计
        if backtest:
            stats = backtest.analyze_performance()
            if "error" not in stats and stats.get("total_recommendations", 0) >= 3:
                result.append(f"📊 策略胜率: {stats['win_rate']}% | 均收益: {stats['avg_profit']}%")

    return "\n".join(result)

def generate_report(report_type="早盘"):
    """生成完整报告 - 清晰简洁版"""
    # 先追踪之前的推荐
    track_recommendations()
    
    now = datetime.now()
    title = f"📈 {report_type}股票建议 {now.strftime('%m/%d %H:%M')}"

    content = []

    # 获取所有持仓数据
    stocks_data = []
    print(f"正在获取 {len(HOLDINGS)} 只股票数据...")
    for name, code in HOLDINGS.items():
        data = get_stock_price(code)
        stocks_data.append((name, code, data))
        time.sleep(0.3)

    # ===== 持仓操作建议 =====
    content.append("━━━━━━━━ 持仓股操作 ━━━━━━━━")
    for name, code, data in stocks_data:
        analysis = analyze_holding(code, name, data)
        content.append(analysis)

    # ===== 激进资金建议 =====
    aggressive = analyze_aggressive_fund(stocks_data, report_type)
    content.append("")
    content.append("━━━━━━━━ 3万激进资金 ━━━━━━━━")
    # 只取关键部分，去掉冗余
    lines = aggressive.split("\n")
    for line in lines:
        if "━━" in line and "3万激进资金" not in line:
            continue
        content.append(line)

    content.append("")
    content.append("━━━━━━━━ 风险提示 ━━━━━━━━")
    content.append("⚠️ 股市有风险，操作需谨慎！")
    content.append(f"生成时间: {now.strftime('%H:%M:%S')}")

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
