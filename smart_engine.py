"""
智能选股引擎 v3.0
核心功能：
1. 市场环境感知 - 判断今天是强势还是弱势
2. 动态策略权重 - 根据近期表现自动调整
3. 多数据源切换 - 东方财富/腾讯/新浪
4. 自我纠错 - 连续失败自动降低权重
5. 全市场扫描 - 从涨幅榜/振幅榜/换手率榜找激进标的
"""

import requests
import time
from datetime import datetime
from collections import defaultdict

class SmartStockEngine:
    def __init__(self):
        self.market_status = None  # 强势/弱势/震荡
        self.strategy_weights = {
            "强势追涨": 1.0,
            "超跌反弹": 1.0,
            "轮动板块": 1.0,
        }
        self.recent_results = []  # 最近10次结果
        self.data_sources = [
            ("腾讯", self.get_qq_data),
            ("新浪", self.get_sina_data),
        ]
    
    def get_qq_data(self, code):
        """腾讯股票API"""
        try:
            market = "sh" if code.startswith("6") else "sz"
            url = f"https://qt.gtimg.cn/q={market}{code}"
            resp = requests.get(url, timeout=5)
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
                    "volume": float(parts[6]),
                    "turnover_rate": float(parts[38]) if len(parts) > 38 and parts[38] else 0,
                }
        except:
            pass
        return None
    
    def get_sina_data(self, code):
        """新浪股票API"""
        try:
            url = f"https://hq.sinajs.cn/list={code}"
            headers = {'Referer': 'http://finance.sina.com.cn'}
            resp = requests.get(url, headers=headers, timeout=5)
            resp.encoding = 'gbk'
            data = resp.text
            parts = data.split('"')[1].split(',')
            
            if len(parts) > 10:
                return {
                    "name": parts[0],
                    "open": float(parts[1]),
                    "close": float(parts[2]),
                    "price": float(parts[3]),
                    "high": float(parts[4]),
                    "low": float(parts[5]),
                    "volume": float(parts[8]),
                    "yesterday_close": float(parts[2]),
                    "change_pct": round((float(parts[3]) - float(parts[2])) / float(parts[2]) * 100, 2),
                }
        except:
            pass
        return None
    
    def get_stock_data(self, code):
        """多数据源获取，自动切换"""
        for name, func in self.data_sources:
            data = func(code)
            if data and data.get("price", 0) > 0:
                return data
        return None
    
    def analyze_market(self, stocks_data):
        """分析市场环境"""
        if not stocks_data:
            return "震荡"
        
        # 计算涨跌比
        up_count = sum(1 for d in stocks_data if d and d.get("change_pct", 0) > 0)
        down_count = sum(1 for d in stocks_data if d and d.get("change_pct", 0) < 0)
        total = len(stocks_data)
        
        # 计算平均涨幅
        changes = [d["change_pct"] for d in stocks_data if d]
        avg_change = sum(changes) / len(changes) if changes else 0
        
        # 计算振幅
        amplitudes = []
        for d in stocks_data:
            if d and d.get("high") and d.get("low") and d.get("yesterday_close"):
                amp = (d["high"] - d["low"]) / d["yesterday_close"] * 100
                amplitudes.append(amp)
        avg_amplitude = sum(amplitudes) / len(amplitudes) if amplitudes else 0
        
        # 判断市场环境
        up_ratio = up_count / total if total > 0 else 0
        
        if up_ratio >= 0.7 and avg_change > 1.5:
            self.market_status = "强势"
            return "强势"
        elif up_ratio <= 0.3 and avg_change < -1.5:
            self.market_status = "弱势"
            return "弱势"
        elif avg_amplitude > 3:
            self.market_status = "震荡"
            return "震荡"
        else:
            self.market_status = "平稳"
            return "平稳"
    
    def update_strategy_result(self, strategy, profit):
        """更新策略表现"""
        self.recent_results.append({
            "strategy": strategy,
            "profit": profit,
            "time": datetime.now()
        })
        
        # 只保留最近10次
        if len(self.recent_results) > 10:
            self.recent_results = self.recent_results[-10:]
        
        # 调整权重：连续失败降低权重
        recent_same = [r for r in self.recent_results[-5:] if r["strategy"] == strategy]
        if len(recent_same) >= 3:
            losses = sum(1 for r in recent_same if r["profit"] < 0)
            if losses >= 3:
                self.strategy_weights[strategy] *= 0.7  # 降低权重30%
                print(f"[引擎] {strategy} 连续失败，权重降低到 {self.strategy_weights[strategy]:.2f}")
            elif losses == 0:
                self.strategy_weights[strategy] = min(1.5, self.strategy_weights[strategy] * 1.1)  # 加权10%
                print(f"[引擎] {strategy} 连续成功，权重提升到 {self.strategy_weights[strategy]:.2f}")
    
    def select_stocks(self, stocks_data, market_status):
        """智能选股"""
        candidates = []
        
        for name, code, data in stocks_data:
            if not data:
                continue
            
            change = data.get("change_pct", 0)
            score = 0
            reasons = []
            
            # 根据市场环境调整选股策略
            if market_status == "强势":
                # 强势市场：追强势股
                if change >= 3:
                    score = 80 + change * 10 + self.strategy_weights.get("强势追涨", 1) * 20
                    reasons.append("强势市场追涨")
                elif change >= 0:
                    score = 50 + change * 5
                    reasons.append("随大盘小涨")
                    
            elif market_status == "弱势":
                # 弱势市场：找超跌反弹
                if change <= -5:
                    score = 70 + abs(change) * 5 + self.strategy_weights.get("超跌反弹", 1) * 15
                    reasons.append("超跌反弹机会")
                elif change <= -2:
                    score = 40 + abs(change) * 3
                    reasons.append("可能见底")
                else:
                    score = 20  # 上涨的反而危险
                    reasons.append("弱势上涨不追")
                    
            elif market_status in ["震荡", "平稳"]:
                # 震荡市场：做差价
                if 2 <= change <= 5:
                    score = 60 + (5 - change) * 10 + self.strategy_weights.get("轮动板块", 1) * 15
                    reasons.append("震荡做T机会")
                elif change <= -3:
                    score = 50 + abs(change) * 5
                    reasons.append("超跌可轻仓")
            
            if score > 0:
                candidates.append({
                    "name": name,
                    "code": code,
                    "data": data,
                    "score": score,
                    "reasons": reasons
                })
        
        # 按分数排序
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates
    
    def generate_recommendation(self, candidates, limit=2):
        """生成推荐"""
        if not candidates:
            return []
        
        recommendations = []
        
        for c in candidates[:limit]:
            data = c["data"]
            price = data["price"]
            change = data["change_pct"]
            
            # 计算建议
            if change > 0:
                buy_price = round(price * 0.995, 2)  # 略低于现价
                strategy = "强势追涨"
            else:
                buy_price = round(price * 0.98, 2)  # 大跌可以低买
                strategy = "超跌反弹"
            
            stop_loss = round(buy_price * 0.97, 2)  # 3%止损
            target = round(buy_price * 1.05, 2)  # 5%目标
            
            recommendations.append({
                "stock": c["name"],
                "code": c["code"],
                "current_price": price,
                "change": change,
                "buy_price": buy_price,
                "stop_loss": stop_loss,
                "target": target,
                "shares": int(10000 / buy_price),
                "strategy": strategy,
                "reason": " + ".join(c["reasons"]),
                "confidence": min(95, int(c["score"]))
            })
        
        return recommendations

    def generate_recommendation_from_market(self, market_targets: list, limit: int = 2) -> list:
        """从全市场扫描结果生成推荐
        
        Args:
            market_targets: market_scanner.scan_aggressive_targets() 的结果
            limit: 最多推荐几只
        
        Returns:
            推荐列表
        """
        if not market_targets:
            return []
        
        recommendations = []
        
        for stock in market_targets[:limit]:
            name = stock.get("name", "未知")
            code = stock.get("code", "")
            price = stock.get("price", 0)
            change = stock.get("change_pct", 0)
            strategy = stock.get("strategy", "未知")
            reason = stock.get("reason", "")
            score = stock.get("score", 50)
            amplitude = stock.get("amplitude", 0)
            turnover_rate = stock.get("turnover_rate", 0)
            
            if price <= 0:
                continue
            
            # 计算买卖价格
            if change > 0:
                buy_price = round(price * 0.998, 2)  # 激进追涨
            else:
                buy_price = round(price * 0.99, 2)  # 超跌低买
            
            stop_loss = round(buy_price * 0.97, 2)  # 3%止损
            target = round(buy_price * 1.05, 2)  # 5%目标
            shares = int(10000 / buy_price)
            
            # 判断操作建议
            if change > 9.5:
                action = "不追"
                detail = "接近涨停，等明天"
                priority = 0
            elif change > 6:
                action = "轻仓试"
                detail = f"建议{int(shares/3)}股"
                shares = int(shares / 3)
                priority = 1
            elif change > 0:
                action = "可以买"
                detail = f"建议{shares}股"
                priority = 2
            elif change > -3:
                action = "观望"
                detail = "等跌更多或反弹再买"
                priority = 1
            elif change > -6:
                action = "超跌买"
                detail = f"建议{shares}股抢反弹"
                priority = 2
            else:
                action = "大跌注意"
                detail = f"建议{int(shares/2)}股，止损严"
                shares = int(shares / 2)
                priority = 1
            
            recommendations.append({
                "stock": name,
                "code": code,
                "current_price": price,
                "change": change,
                "buy_price": buy_price,
                "stop_loss": stop_loss,
                "target": target,
                "shares": shares,
                "strategy": strategy,
                "reason": reason,
                "action": action,
                "detail": detail,
                "amplitude": amplitude,
                "turnover_rate": turnover_rate,
                "score": score,
                "priority": priority,
                "confidence": min(90, int(score)),
            })
        
        # 按优先级和分数排序
        recommendations.sort(key=lambda x: (x["priority"], x["score"]), reverse=True)
        
        # 更新策略表现
        for rec in recommendations:
            if rec["priority"] >= 2:  # 真正建议买入的
                self.update_strategy_result(rec["strategy"], 0)  # 记录推荐，等待后续更新盈亏
        
        return recommendations


def test_engine():
    """测试引擎"""
    engine = SmartStockEngine()
    
    # 测试数据
    test_stocks = [
        ("信维通信", "300136"),
        ("斯瑞新材", "688102"),
    ]
    
    stocks_data = []
    for name, code in test_stocks:
        data = engine.get_stock_data(code)
        stocks_data.append((name, code, data))
        time.sleep(0.3)
    
    # 分析市场
    market = engine.analyze_market([d for _, _, d in stocks_data if d])
    print(f"\n市场环境: {market}")
    
    # 选股
    candidates = engine.select_stocks(stocks_data, market)
    print(f"\n候选股票: {len(candidates)} 只")
    
    # 生成推荐
    recs = engine.generate_recommendation(candidates)
    print(f"\n推荐股票: {len(recs)} 只")
    
    for r in recs:
        print(f"\n◆ {r['stock']}({r['code']})")
        print(f"  现价: {r['current_price']} 涨幅: {r['change']:+.1f}%")
        print(f"  建议买价: {r['buy_price']} 止损: {r['stop_loss']}")
        print(f"  策略: {r['strategy']} 置信度: {r['confidence']}%")
        print(f"  理由: {r['reason']}")


if __name__ == "__main__":
    test_engine()
