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
    from position_state import PositionState
    HAS_SMART = True
    HAS_SCANNER = True
    HAS_POSITION_STATE = True
except Exception as e:
    print(f"导入智能模块失败: {e}")
    HAS_SMART = False
    HAS_SCANNER = False
    HAS_POSITION_STATE = False

# ============ 配置 ============
SEND_KEY = "SCT334455TmE1WOH5QWyW2WU61yptgszVi"

# 激进资金 (5-8万)
AGGRESSIVE_MONEY = 80000

# 初始化系统
backtest = BacktestSystem() if HAS_SMART else None
smart_engine = SmartStockEngine() if HAS_SMART else None
market_scanner = MarketScanner() if HAS_SCANNER else None
position_state = PositionState() if HAS_POSITION_STATE else None

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
        buy_price = rec.get("buy_price")
        if buy_price is None:
            buy_price = current_price

        if buy_price and buy_price > 0:
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

# 激进资金 (5-8万)
AGGRESSIVE_MONEY = 80000

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

def get_market_index():
    """获取大盘指数判断整体趋势"""
    try:
        # 沪深300指数
        url = "https://qt.gtimg.cn/q=sh000300"
        resp = requests.get(url, timeout=5)
        resp.encoding = 'gbk'
        data = resp.text.split('~')
        if len(data) > 4:
            close = float(data[3])
            yesterday = float(data[4])
            change = (close - yesterday) / yesterday * 100
            return {
                "name": "沪深300",
                "change": round(change, 2),
                "trend": "强势" if change > 1 else ("弱势" if change < -1 else "震荡")
            }
    except:
        pass
    return {"name": "沪深300", "change": 0, "trend": "震荡"}

def analyze_holding_flexible(code, name, data, market_index):
    """持仓分析 - 灵活策略版
    
    根据大盘环境和个股走势动态调整建议
    """
    if not data:
        return f"【{name}】数据获取失败"

    price = data["price"]
    change_pct = data["change_pct"]
    market_trend = market_index.get("trend", "震荡")
    market_change = market_index.get("change", 0)

    # ===== 第一步：判断个股相对大盘的表现 =====
    relative_strength = change_pct - market_change  # 个股相对大盘的超额收益

    # ===== 第二步：根据背景动态调整阈值 =====
    # 当前背景：地缘缓和预期
    # - 军工可能承压
    # - 科技/消费可能受益
    # - 不要死盯固定阈值

    advice = []
    action_emoji = ""
    action_text = ""

    # 判断个股性质
    is_defense_stock = any(k in name for k in ["军工", "国防", "航天", "航发", "兵装", "北方", "中兵"])
    is_tech_stock = any(k in name for k in ["科技", "电子", "通信", "软件", "芯片", "半导体"])
    is_consumption = any(k in name for k in ["消费", "食品", "家电", "零售"])

    # ===== 灵活策略判断 =====
    if is_defense_stock and market_trend == "弱势":
        # 地缘缓和 + 市场弱 = 军工双重承压
        if change_pct > 0:
            advice.append("⚠️ 地缘缓和预期，军工承压")
            advice.append("→ 建议减仓或卖出")
        else:
            advice.append("⚠️ 军工双重杀跌，控制风险")
            advice.append("→ 止损或减仓为主")
        action_emoji = "🔴"
        action_text = "减仓"

    elif is_tech_stock and market_trend == "强势":
        # 强势市场 + 科技受益
        if change_pct > 3:
            advice.append("✅ 强势市场+科技主线持有")
            advice.append("→ 继续持有，等更高点")
            action_emoji = "🟢"
            action_text = "持有"
        elif change_pct > 0:
            advice.append("📈 科技股随大盘上涨")
            advice.append("→ 可以继续持有")
            action_emoji = "🟢"
            action_text = "持有"
        else:
            advice.append("🔵 强势市场小跌，可能是机会")
            advice.append("→ 不卖，等反弹")
            action_emoji = "🔵"
            action_text = "观望"

    elif market_trend == "强势":
        # 大盘强势时的通用策略
        if change_pct > 5:
            advice.append("📈 大盘强势，个股大涨")
            advice.append("→ 可以分批减半，留底仓")
            action_emoji = "🟠"
            action_text = "减半仓"
        elif change_pct > 2:
            advice.append("✅ 随大盘上涨，继续持有")
            advice.append("→ 不追高也不卖，等信号")
            action_emoji = "🟢"
            action_text = "持有"
        elif change_pct > -2:
            advice.append("🔵 大盘强，个股小跌很正常")
            advice.append("→ 不动，等轮动")
            action_emoji = "🔵"
            action_text = "观望"
        else:
            advice.append("🔴 大盘强它却大跌？")
            advice.append("→ 注意，可能是基本面问题")
            advice.append(f"  考虑止损，跌破{round(price*0.97, 2)}必须走")
            action_emoji = "🔴"
            action_text = "止损"

    elif market_trend == "弱势":
        # 大盘弱势时的策略
        if change_pct > 0:
            advice.append("⚠️ 大盘弱，它却逆势上涨")
            if relative_strength > 3:
                advice.append("→ 强于大盘！但也要小心")
                advice.append("  可以减1/3，落袋为安")
                action_emoji = "🟠"
                action_text = "减1/3"
            else:
                advice.append("→ 继续观察，不追")
                action_emoji = "🔵"
                action_text = "观望"
        elif change_pct > -3:
            advice.append("🔵 大盘弱，个股小跌正常")
            advice.append("→ 不买不卖，等机会")
            action_emoji = "🔵"
            action_text = "观望"
        else:
            advice.append("🔴 大盘弱+个股大跌")
            advice.append("→ 控制仓位，减半仓")
            advice.append(f"  止损线：{round(price*0.95, 2)}元")
            action_emoji = "🔴"
            action_text = "减半仓"

    else:  # 震荡市场
        # 震荡市的灵活操作
        if change_pct > 3:
            advice.append("📈 震荡中上涨，可以卖一半")
            advice.append(f"→ 回调到{round(price*0.98, 2)}再买回")
            action_emoji = "🟠"
            action_text = "卖一半"
        elif change_pct > 0:
            advice.append("🔵 震荡小涨，不动")
            advice.append("→ 太小了，等机会")
            action_emoji = "🔵"
            action_text = "观望"
        elif change_pct > -3:
            advice.append("🔵 震荡小跌，可以买一点")
            advice.append(f"→ 最多买1/3仓")
            action_emoji = "🔵"
            action_text = "轻仓试"
        else:
            advice.append("🔴 震荡大跌，注意风险")
            advice.append(f"→ 止损{round(price*0.97, 2)}元")
            action_emoji = "🔴"
            action_text = "止损"

    # ===== 组装输出 =====
    result = f"【{name}】{price}元 {change_pct:+.1f}%"
    result += f"\n→ {action_emoji} {action_text}"
    for line in advice:
        result += f"\n  {line}"

    return result


def analyze_holding(code, name, data):
    """兼容旧版本的持仓分析 - 默认使用灵活策略"""
    market_index = get_market_index()
    return analyze_holding_flexible(code, name, data, market_index)

def analyze_aggressive_fund(stocks_data, report_type):
    """3万激进资金 - 全市场扫描版 v2.1（带止盈止损）
    
    每次推送前检查持仓股盈亏状态：
    - 涨超5% → 卖出一半止盈
    - 跌超3% → 止损
    """
    result = []
    sorted_stocks = sorted(stocks_data, key=lambda x: x[2]["change_pct"] if x[2] else 0, reverse=True)
    
    # ========== 检查仓位状态 ==========
    if position_state:
        position_state.reset_daily()
        state_summary = position_state.get_status_summary()
    
    # ========== 分析市场环境 ==========
    market = "震荡"
    if smart_engine:
        valid_data = [d for _, _, d in stocks_data if d]
        market = smart_engine.analyze_market(valid_data)
    
    # ========== 早盘：全市场扫描找标的 ==========
    if report_type == "早盘":
        result.append(f"📊 市场: {market}市")

        # ========== 先显示仓位状态 ==========
        if position_state:
            positions = position_state.get_positions()
            today_actions = position_state.get_today_actions()
            
            if positions:
                result.append("")
                result.append("💼 【当前激进仓位】")
                invested = sum(p["price"] * p["shares"] for p in positions)
                result.append(f"   持仓{len(positions)}只，约{int(invested)}元")
                for p in positions:
                    result.append(f"   • {p['stock_name']}({p['stock_code']}) {p['shares']}股")
            
            if today_actions:
                result.append("")
                result.append("📋 今日已操作:")
                for a in today_actions:
                    result.append(f"   [{a['time']}] {a['type']}: {a['detail']}")

        # ========== 【重点】检查持仓股止盈/止损 ==========
        if position_state:
            positions = position_state.get_positions()
            if positions:
                result.append("")
                result.append("🎯 【持仓股止盈止损检查】")
                
                has_action = False  # 标记是否有止盈/止损建议
                for p in positions:
                    stock_code = p["stock_code"]
                    stock_name = p["stock_name"]
                    buy_price = p["price"]
                    shares = p["shares"]
                    
                    # 获取实时价格
                    current_data = get_stock_price(stock_code)
                    if not current_data:
                        continue
                    
                    current_price = current_data["price"]
                    change_pct = current_data["change_pct"]
                    
                    # 计算持仓盈亏（从买入价）
                    profit_pct = (current_price - buy_price) / buy_price * 100
                    
                    # 止盈：涨幅超过5%
                    if profit_pct >= 5:
                        sell_shares = shares // 2
                        sell_value = int(sell_shares * current_price)
                        remain_shares = shares - sell_shares
                        if sell_shares > 0:
                            result.append("")
                            result.append(f"🔥 【{stock_name}({stock_code}) 止盈！】")
                            result.append(f"   {buy_price} → {current_price} (+{profit_pct:.1f}%)")
                            result.append(f"   → 【卖半仓】立即卖出 {sell_shares} 股（约{sell_value}元）")
                            result.append(f"   → 剩余 {remain_shares} 股继续持有")
                            result.append(f"   止损位: {round(buy_price * 0.97, 2)}元")
                            has_action = True
                            # 记录减仓操作
                            position_state.reduce_position(stock_code, f"止盈+{profit_pct:.1f}%")
                    
                    # 止损：跌幅超过3%
                    elif profit_pct <= -3:
                        sell_value = int(shares * current_price)
                        loss = round((buy_price - current_price) * shares, 0)
                        result.append("")
                        result.append(f"🚨 【{stock_name}({stock_code}) 必须止损！】")
                        result.append(f"   {buy_price} → {current_price} ({profit_pct:.1f}%)")
                        result.append(f"   → 【卖全仓】立即全部卖出 {shares} 股（约{sell_value}元）")
                        result.append(f"   → 亏损约 {int(loss)} 元")
                        result.append(f"   ⚠️ 严格执行止损纪律！")
                        has_action = True
                        # 记录清仓操作
                        position_state.close_position(stock_code, f"止损{profit_pct:.1f}%")
                    
                    # 正常持有
                    else:
                        result.append("")
                        result.append(f"📌 {stock_name}({stock_code}) {shares}股")
                        result.append(f"   {buy_price} → {current_price} ({profit_pct:+.1f}%)")
                        result.append(f"   → 继续持有，止损位: {round(buy_price * 0.97, 2)}元")
                
                # 如果有止盈/止损动作，保存状态
                if has_action:
                    position_state.save()

        # 使用全市场扫描器（仅在没有持仓或持仓无需操作时推荐新标的）
        remaining_money = AGGRESSIVE_MONEY
        if position_state:
            positions = position_state.get_positions()
            if positions:
                invested = sum(p["price"] * p["shares"] for p in positions)
                remaining_money = AGGRESSIVE_MONEY - invested
                if remaining_money <= 0:
                    result.append("")
                    result.append("⚠️ 激进资金已满仓，不追新标的")
                    result.append("")
                    result.append("📌 激进资金节奏:")
                    result.append("⚡ 早盘: 已建仓完毕")
                    result.append("⏰ 午盘: 检查仓位")
                    result.append("🌙 收盘: 复盘不动手")
                    return "\n".join(result)
        
        if remaining_money >= 5000 and market_scanner:
            print("[激进资金] 开始全市场扫描...")
            market_targets = market_scanner.scan_aggressive_targets(market)

            # 筛选出值得买的标的（涨幅0~6% 或 跌幅-6%~-3%）
            buy_targets = []
            for t in market_targets:
                change = t.get("change_pct", 0)
                price = t.get("price", 0)
                code = t.get("code", "")
                
                if price <= 0:
                    continue
                
                # ========== 检查仓位状态：今天已操作过的跳过 ==========
                if position_state:
                    should_skip, skip_reason = position_state.should_avoid_conflict("建仓", code)
                    if should_skip:
                        continue
                
                # 涨幅0~6%之间可以考虑买
                if 0 <= change <= 6:
                    buy_targets.append((t, "追涨", int(10000 / price)))
                # 跌幅-6%~-3%可以考虑抢反弹
                elif -6 <= change < -3:
                    buy_targets.append((t, "超跌反弹", int(10000 / price)))
                # 涨幅6~9.5%轻仓
                elif 6 < change < 9.5:
                    buy_targets.append((t, "轻仓", int(3000 / price)))

            if buy_targets:
                result.append("")
                result.append("🔥 【早盘激进资金推荐】")

                for i, (t, strategy, shares) in enumerate(buy_targets[:2], 1):
                    name = t.get("name", "未知")
                    code = t.get("code", "")
                    price = t.get("price", 0)
                    change = t.get("change_pct", 0)
                    reason = t.get("reason", "")

                    stop_loss = round(price * 0.97, 2)
                    buy_value = int(shares * price)

                    # 价格风险提示
                    risk_warn = ""
                    if change >= 9:
                        risk_warn = " ⚠️ 涨幅已高，追高风险大！"
                    elif change >= 7:
                        risk_warn = " ⚠️ 涨幅偏高，注意风险"

                    result.append("")
                    result.append(f"#{i} {name}({code}) {change:+.1f}%{risk_warn}")
                    result.append(f"   → 买入{shares}股（约{buy_value}元）")
                    result.append(f"   策略: {strategy} | 止损: {stop_loss}元")
                    result.append(f"   原因: {reason}")
                    result.append(f"   📌 以市价立即买入！")

                    # 记录到回测系统和仓位状态
                    if backtest and shares > 0:
                        t["price"] = price
                        t["change_pct"] = change
                        record_recommendation(name, code, t, strategy, reason, "早盘")
                        position_state.add_position(code, name, price, shares, strategy, reason)
            else:
                result.append("")
                result.append("❌ 今日无合适标的")
                result.append("   建议空仓观望，等待机会")
        else:
            result.append("⚠️ 扫描器未加载")

            # 激进资金节奏提醒
            result.append("")
            result.append("📌 激进资金节奏:")
            result.append("⚡ 早盘: 找机会建仓")
            result.append("⏰ 午盘: 检查仓位")
            result.append("🌙 收盘: 复盘不动手")

    elif report_type == "午盘":
        result.append(f"📊 市场: {market}市")

        # ========== 【核心】先检查持仓股的止盈/止损 ==========
        if position_state:
            positions = position_state.get_positions()
            today_actions = position_state.get_today_actions()
            
            if positions:
                result.append("")
                result.append("💼 【激进资金持仓检查】")
                
                has_action_today = False  # 今天是否已有操作
                for p in positions:
                    code = p["stock_code"]
                    name = p["stock_name"]
                    buy_price = p["price"]
                    shares = p["shares"]
                    buy_time = p.get("buy_time", "")
                    
                    # 检查今天是否已对这个股票操作过
                    already_actioned = False
                    for a in today_actions:
                        if code in str(a.get("detail", "")):
                            already_actioned = True
                            break
                    
                    # 获取实时价格
                    try:
                        data = get_stock_price(code)
                        if data and data.get("price"):
                            current_price = data["price"]
                            profit_pct = (current_price - buy_price) / buy_price * 100
                            
                            if already_actioned:
                                # 今天已操作过，只显示状态
                                result.append("")
                                result.append(f"📌 {name}({code}) {shares}股")
                                result.append(f"   成本{buy_price} → 现价{current_price} ({profit_pct:+.1f}%)")
                                result.append(f"   → 今日已操作，继续持有")
                            else:
                                # 止盈检查：涨超5%
                                if profit_pct >= 5:
                                    sell_shares = shares // 2  # 卖一半
                                    sell_value = int(sell_shares * current_price)
                                    keep_shares = shares - sell_shares
                                    result.append("")
                                    result.append(f"🎯 【{name}({code}) 止盈！】")
                                    result.append(f"   成本 {buy_price} → 现价 {current_price} ({profit_pct:+.1f}%)")
                                    result.append(f"   → 【卖半仓】立即卖出 {sell_shares} 股（约 {sell_value} 元）")
                                    result.append(f"   → 剩余 {keep_shares} 股继续持有")
                                    position_state.reduce_position(code, f"止盈+{profit_pct:.1f}%")
                                    has_action_today = True
                                # 止损检查：跌超3%
                                elif profit_pct <= -3:
                                    sell_value = int(shares * current_price)
                                    result.append("")
                                    result.append(f"🚨 【{name}({code}) 必须止损！】")
                                    result.append(f"   成本 {buy_price} → 现价 {current_price}")
                                    result.append(f"   持仓亏损: {profit_pct:+.1f}%")
                                    result.append(f"   → 【卖全仓】立即全部卖出 {shares} 股（约 {sell_value} 元）")
                                    result.append(f"   ⚠️ 严格执行止损纪律！")
                                    position_state.close_position(code, f"止损{profit_pct:.1f}%")
                                    has_action_today = True
                                # 正常持有
                                else:
                                    result.append("")
                                    result.append(f"📌 {name}({code}) {shares}股")
                                    result.append(f"   成本{buy_price} → 现价{current_price} ({profit_pct:+.1f}%)")
                                    result.append(f"   → 继续持有观望")
                    except Exception as e:
                        result.append(f"   {name}: 价格获取失败")
            
            # 今日操作总结
            if today_actions:
                result.append("")
                result.append("📋 今日已操作:")
                for a in today_actions:
                    t = a.get("time", "")
                    ty = a.get("type", "")
                    d = a.get("detail", "")
                    result.append(f"   [{t}] {ty}: {d}")
        
        # ========== 检查是否已建仓过 ==========
        if position_state:
            positions = position_state.get_positions()
            if len(positions) >= 2:
                result.append("")
                result.append("⚠️ 午盘：已有2只持仓，暂不追新")
            else:
                # 午盘再扫一次全市场
                if market_scanner:
                    market_targets = market_scanner.scan_aggressive_targets(market)
                    buy_targets = []
                    for t in market_targets:
                        change = t.get("change_pct", 0)
                        price = t.get("price", 0)
                        code = t.get("code", "")
                        
                        if price <= 0:
                            continue
                        
                        # 检查仓位状态
                        if position_state:
                            should_skip, skip_reason = position_state.should_avoid_conflict("建仓", code)
                            if should_skip:
                                continue
                        
                        if 0 <= change <= 6:
                            buy_targets.append((t, "追涨", int(10000 / price)))
                        elif -6 <= change < -3:
                            buy_targets.append((t, "超跌反弹", int(10000 / price)))
                        elif 6 < change < 9.5:
                            buy_targets.append((t, "轻仓", int(3000 / price)))

                    if buy_targets:
                        result.append("")
                        result.append("🔥 【午盘新机会】:")
                        for i, (t, strategy, shares) in enumerate(buy_targets[:1], 1):
                            name = t.get("name", "未知")
                            code = t.get("code", "")
                            price = t.get("price", 0)
                            change = t.get("change_pct", 0)
                            stop_loss = round(price * 0.97, 2)
                            buy_value = int(shares * price)
                            risk_warn = " ⚠️ 涨幅已高！" if change >= 9 else ""
                            result.append(f"#{i} {name}({code}) {change:+.1f}%{risk_warn}")
                            result.append(f"   → 买入{shares}股（约{buy_value}元）| 止损:{stop_loss}元")
                            result.append(f"   📌 以市价立即买入！")

                            if backtest and shares > 0:
                                t["price"] = price
                                record_recommendation(name, code, t, strategy, f"午盘{strategy}", "午盘")
                                position_state.add_position(code, name, price, shares, strategy, f"午盘{strategy}")
                else:
                    result.append("❌ 午盘无新机会")

        result.append("")
        result.append("⏰ 14:37 收盘不复盘，只复盘！")

    elif report_type == "盘中":
        result.append(f"📊 市场: {market}市")

        # ========== 盘中：检查持仓 + 找盘中机会 ==========
        if position_state:
            positions = position_state.get_positions()
            today_actions = position_state.get_today_actions()

            # 【核心】先检查持仓股的止盈/止损
            if positions:
                result.append("")
                result.append("💼 【激进资金持仓检查】")

                has_action_today = False
                for p in positions:
                    code = p["stock_code"]
                    name = p["stock_name"]
                    buy_price = p["price"]
                    shares = p["shares"]

                    # 检查今天是否已操作
                    already_actioned = False
                    for a in today_actions:
                        if code in str(a.get("detail", "")):
                            already_actioned = True
                            break

                    # 获取实时价格
                    try:
                        data = get_stock_price(code)
                        if data and data.get("price"):
                            current_price = data["price"]
                            profit_pct = (current_price - buy_price) / buy_price * 100

                            if already_actioned:
                                result.append("")
                                result.append(f"📌 {name}({code}) {shares}股")
                                result.append(f"   成本{buy_price} → 现价{current_price} ({profit_pct:+.1f}%)")
                                result.append(f"   → 今日已操作，继续持有")
                            else:
                                # 止盈：涨超5%
                                if profit_pct >= 5:
                                    sell_shares = shares // 2
                                    sell_value = int(sell_shares * current_price)
                                    keep_shares = shares - sell_shares
                                    result.append("")
                                    result.append(f"🎯 【{name}({code}) 止盈！】")
                                    result.append(f"   成本 {buy_price} → 现价 {current_price} ({profit_pct:+.1f}%)")
                                    result.append(f"   → 【卖半仓】立即卖出 {sell_shares} 股（约 {sell_value} 元）")
                                    result.append(f"   → 剩余 {keep_shares} 股继续持有")
                                    position_state.reduce_position(code, f"止盈+{profit_pct:.1f}%")
                                    has_action_today = True
                                # 止损：跌超3%
                                elif profit_pct <= -3:
                                    sell_value = int(shares * current_price)
                                    result.append("")
                                    result.append(f"🚨 【{name}({code}) 必须止损！】")
                                    result.append(f"   成本 {buy_price} → 现价 {current_price}")
                                    result.append(f"   持仓亏损: {profit_pct:+.1f}%")
                                    result.append(f"   → 【卖全仓】立即全部卖出 {shares} 股（约 {sell_value} 元）")
                                    result.append(f"   ⚠️ 严格执行止损纪律！")
                                    position_state.close_position(code, f"止损{profit_pct:.1f}%")
                                    has_action_today = True
                                # 正常持有
                                else:
                                    result.append("")
                                    result.append(f"📌 {name}({code}) {shares}股")
                                    result.append(f"   成本{buy_price} → 现价{current_price} ({profit_pct:+.1f}%)")
                                    result.append(f"   → 继续持有")
                                    # 盘中可以考虑加仓
                                    if profit_pct >= 2 and len(positions) < 2:
                                        add_shares = int(5000 / current_price)
                                        if add_shares > 0:
                                            result.append(f"   → 【可考虑加仓】{add_shares}股（约{int(add_shares*current_price)}元）")
                    except Exception as e:
                        result.append(f"   {name}: 价格获取失败")

            # 今日操作总结
            if today_actions:
                result.append("")
                result.append("📋 今日已操作:")
                for a in today_actions:
                    t = a.get("time", "")
                    ty = a.get("type", "")
                    d = a.get("detail", "")
                    result.append(f"   [{t}] {ty}: {d}")

        # ========== 盘中找机会（条件更严格）==========
        if position_state:
            positions = position_state.get_positions()
            if len(positions) >= 2:
                result.append("")
                result.append("⚠️ 盘中：已有2只持仓，暂不追新")
            else:
                if market_scanner:
                    market_targets = market_scanner.scan_aggressive_targets(market)
                    buy_targets = []
                    for t in market_targets:
                        change = t.get("change_pct", 0)
                        price = t.get("price", 0)
                        code = t.get("code", "")

                        if price <= 0:
                            continue

                        # 检查仓位状态
                        if position_state:
                            should_skip, skip_reason = position_state.should_avoid_conflict("建仓", code)
                            if should_skip:
                                continue

                        # 盘中条件更严格：涨幅0-4%
                        if 0 <= change <= 4:
                            buy_targets.append((t, "追涨", int(10000 / price)))
                        elif -5 <= change < -2:
                            buy_targets.append((t, "超跌反弹", int(8000 / price)))

                    if buy_targets:
                        result.append("")
                        result.append("🔥 【盘中机会】:")
                        for i, (t, strategy, shares) in enumerate(buy_targets[:1], 1):
                            name = t.get("name", "未知")
                            code = t.get("code", "")
                            price = t.get("price", 0)
                            change = t.get("change_pct", 0)
                            stop_loss = round(price * 0.97, 2)
                            buy_value = int(shares * price)
                            result.append(f"#{i} {name}({code}) {change:+.1f}%")
                            result.append(f"   → 买入{shares}股（约{buy_value}元）| 止损:{stop_loss}元")
                            result.append(f"   📌 以市价买入")

                            if backtest and shares > 0:
                                t["price"] = price
                                record_recommendation(name, code, t, strategy, f"盘中{strategy}", "盘中")
                                position_state.add_position(code, name, price, shares, strategy, f"盘中{strategy}")
                    else:
                        result.append("❌ 盘中无合适机会")

        result.append("")
        result.append("⏰ 12:30 午盘继续检查仓位")
        result.append("⏰ 14:37 收盘不复盘，只复盘！")

    else:  # 收盘
        result.append(f"📊 今日市场: {market}市")

        # ========== 【核心】收盘前最后一次检查止盈/止损 ==========
        if position_state:
            positions = position_state.get_positions()
            today_actions = position_state.get_today_actions()
            
            result.append("")
            result.append("💼 【激进资金收盘检查】")

            if positions:
                for p in positions:
                    code = p["stock_code"]
                    name = p["stock_name"]
                    buy_price = p["price"]
                    shares = p["shares"]
                    
                    # 检查今天是否已操作过
                    already_actioned = False
                    for a in today_actions:
                        if code in str(a.get("detail", "")):
                            already_actioned = True
                            break
                    
                    # 获取实时价格
                    try:
                        data = get_stock_price(code)
                        if data and data.get("price"):
                            current_price = data["price"]
                            profit_pct = (current_price - buy_price) / buy_price * 100
                            
                            if already_actioned:
                                # 今天已操作过
                                result.append("")
                                result.append(f"📌 {name}({code}) {shares}股")
                                result.append(f"   {buy_price} → {current_price} ({profit_pct:+.1f}%)")
                                result.append(f"   → 今日已操作，明日继续持有")
                            elif profit_pct >= 5:
                                # 止盈
                                sell_shares = shares // 2
                                sell_value = int(sell_shares * current_price)
                                result.append("")
                                result.append(f"🎯 【{name}({code}) 今日止盈！】")
                                result.append(f"   {buy_price} → {current_price} ({profit_pct:+.1f}%)")
                                result.append(f"   → 明日开盘卖出 {sell_shares} 股（约{sell_value}元）")
                                result.append(f"   → 剩余 {shares - sell_shares} 股继续持有")
                            elif profit_pct <= -3:
                                # 止损
                                sell_value = int(shares * current_price)
                                result.append("")
                                result.append(f"🚨 【{name}({code}) 必须止损！】")
                                result.append(f"   {buy_price} → {current_price} ({profit_pct:+.1f}%)")
                                result.append(f"   → 明日开盘全部卖出 {shares} 股（约{sell_value}元）")
                                result.append(f"   ⚠️ 严格执行纪律！")
                            else:
                                # 正常
                                result.append("")
                                result.append(f"📌 {name}({code}) {shares}股")
                                result.append(f"   {buy_price} → {current_price} ({profit_pct:+.1f}%)")
                                result.append(f"   → 明日继续持有观望")
                    except Exception as e:
                        result.append(f"   {name}: 价格获取失败")
            
            # 今日操作总结
            if today_actions:
                result.append("")
                result.append("📋 今日操作记录:")
                for a in today_actions:
                    t = a.get("time", "")
                    ty = a.get("type", "")
                    d = a.get("detail", "")
                    result.append(f"   [{t}] {ty}: {d}")
            else:
                result.append("")
                result.append("📋 今日操作: 无操作")
        
        # 明日计划
        result.append("")
        result.append("🌙 【明日激进资金计划】")
        if position_state:
            positions = position_state.get_positions()
            if not positions:
                result.append("   激进资金空仓，明日可建仓")
            elif len(positions) < 2:
                result.append(f"   激进资金半仓({len(positions)}只)，明日可继续建仓")
            else:
                result.append("   激进资金已满仓，明日以持仓为主")
        
        result.append("")
        result.append("⚠️ 核心纪律: 亏3%必须止损！涨5%卖一半！")
        result.append("")
        result.append("🔔 尾盘30分钟不建新仓！")

        # 回测统计
        if backtest:
            stats = backtest.analyze_performance()
            if "error" not in stats and stats.get("total_recommendations", 0) >= 3:
                result.append(f"📊 当前策略胜率: {stats['win_rate']}%")

    return "\n".join(result)

def is_trading_day():
    """检查今天是否是交易日"""
    now = datetime.now()
    
    # 1. 检查周末
    if now.weekday() >= 5:  # 周六=5, 周日=6
        return False, "今天是周末，休市"
    
    # 2. 检查主要节假日（硬编码，够用）
    month_day = now.strftime("%m-%d")
    holidays_2026 = [
        "01-01",  # 元旦
        "01-28", "01-29", "01-30", "01-31", "02-01", "02-02",  # 春节
        "04-03", "04-04", "04-05",  # 清明
        "05-01", "05-02", "05-03",  # 劳动节
        "06-01",  # 端午
        "09-03", "09-04", "09-05",  # 抗战纪念日
        "10-01", "10-02", "10-03", "10-04", "10-05", "10-06", "10-07",  # 国庆
    ]
    
    if month_day in holidays_2026:
        return False, f"今天是法定节假日({month_day})，休市"
    
    return True, ""

def generate_report(report_type="早盘"):
    """生成完整报告 - iPhone手机友好版"""
    now = datetime.now()
    
    # ===== 检查是否为交易日 =====
    is_trading, msg = is_trading_day()
    if not is_trading:
        title = f"📅 {now.strftime('%m/%d')} 非交易日"
        content = [
            f"❌ {msg}",
            "",
            "📌 明天正常交易时段再见",
            "💼 持仓股继续持有",
            f"🕐 {now.strftime('%H:%M:%S')}"
        ]
        return title, "\n".join(content)
    
    # 先追踪之前的推荐
    track_recommendations()

    title = f"📈 {report_type}建议 {now.strftime('%m/%d %H:%M')}"

    content = []

    # ===== 大盘环境（简洁一行）=====
    print("正在获取大盘指数...")
    market_index = get_market_index()
    market_emoji = "🔥" if market_index['change'] > 0 else "❄️"
    content.append(f"{market_emoji} {market_index['name']} {market_index['change']:+.2f}% ({market_index['trend']}市)")
    content.append("")

    # ===== 持仓操作建议 =====
    content.append("━━━ 持仓股 ━━━")

    # 获取所有持仓数据
    stocks_data = []
    print(f"正在获取 {len(HOLDINGS)} 只股票数据...")
    for name, code in HOLDINGS.items():
        data = get_stock_price(code)
        stocks_data.append((name, code, data))

    for name, code, data in stocks_data:
        analysis = analyze_holding_flexible(code, name, data, market_index)
        lines = analysis.split("\n")
        for line in lines:
            if line.strip():
                content.append(line)

    # ===== 激进资金建议 =====
    aggressive = analyze_aggressive_fund(stocks_data, report_type)
    content.append("")
    content.append("━━━ 3万激进资金 ━━━")
    lines = aggressive.split("\n")
    skip_next = False
    for i, line in enumerate(lines):
        # 跳过冗余的分隔线
        if "━━" in line and ("激进资金" not in line or lines[i-1] if i > 0 else "").endswith(":"):
            continue
        if "━━━━" in line:
            continue
        if line.strip():
            content.append(line)

    content.append("")
    content.append("━━━ 风险提示 ━━━")
    content.append("⚠️ 股市有风险，操作需谨慎！")
    content.append(f"🕐 {now.strftime('%H:%M:%S')}")

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
