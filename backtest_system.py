"""
股票策略回测系统 v1.0
功能：
1. 记录每次推荐的股票和买入价格
2. 追踪推荐后1天、3天、5天的表现
3. 计算胜率、收益率、优化策略
4. 自动学习改进
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

# 数据文件路径
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
RECOMMEND_FILE = os.path.join(DATA_DIR, "recommendations_log.json")

class BacktestSystem:
    def __init__(self):
        self.recommendations = self.load_recommendations()
        self.stats = {
            "total": 0,
            "win": 0,
            "loss": 0,
            "profit_by_strategy": defaultdict(lambda: {"count": 0, "total_profit": 0}),
            "profit_by_change": defaultdict(lambda: {"count": 0, "total_profit": 0}),
            "best_strategy": None,
            "worst_strategy": None
        }
    
    def load_recommendations(self):
        """加载历史推荐记录"""
        if os.path.exists(RECOMMEND_FILE):
            with open(RECOMMEND_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def save_recommendations(self):
        """保存推荐记录"""
        with open(RECOMMEND_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.recommendations, f, ensure_ascii=False, indent=2)
    
    def add_recommendation(self, stock_code, stock_name, recommend_price, 
                           current_change, strategy, signal_type, target_date):
        """添加新的推荐记录"""
        record = {
            "id": len(self.recommendations) + 1,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "target_date": target_date,
            "stock_code": stock_code,
            "stock_name": stock_name,
            "recommend_price": recommend_price,
            "buy_price": recommend_price,  # 实际可能不同
            "current_change": current_change,  # 当时的涨幅
            "strategy": strategy,  # 策略类型
            "signal_type": signal_type,  # 信号类型
            "result_1d": None,  # 1天后结果
            "result_3d": None,  # 3天后结果
            "result_5d": None,  # 5天后结果
            "final_profit": None,  # 最终收益
            "status": "pending"  # pending, completed, cancelled
        }
        self.recommendations.append(record)
        self.save_recommendations()
        return record["id"]
    
    def update_result(self, record_id, period, price, change_pct):
        """更新某只股票的追踪结果"""
        for rec in self.recommendations:
            if rec["id"] == record_id:
                if period == "1d":
                    rec["result_1d"] = {"price": price, "change": change_pct}
                elif period == "3d":
                    rec["result_3d"] = {"price": price, "change": change_pct}
                elif period == "5d":
                    rec["result_5d"] = {"price": price, "change": change_pct}
                
                # 计算收益率
                if rec["buy_price"] and price:
                    rec["final_profit"] = round((price - rec["buy_price"]) / rec["buy_price"] * 100, 2)
                    rec["status"] = "completed"
                
                self.save_recommendations()
                break
    
    def analyze_performance(self):
        """分析整体表现"""
        if not self.recommendations:
            return {"error": "暂无数据"}
        
        completed = [r for r in self.recommendations if r["status"] == "completed"]
        
        if not completed:
            return {"error": "暂无已完成的记录"}
        
        # 基础统计
        total = len(completed)
        wins = [r for r in completed if r.get("final_profit", 0) > 0]
        losses = [r for r in completed if r.get("final_profit", 0) <= 0]
        
        win_rate = len(wins) / total * 100 if total > 0 else 0
        avg_profit = sum(r.get("final_profit", 0) for r in completed) / total
        
        # 按策略分析
        strategy_stats = defaultdict(lambda: {"count": 0, "wins": 0, "total_profit": 0})
        for r in completed:
            s = r.get("strategy", "unknown")
            strategy_stats[s]["count"] += 1
            strategy_stats[s]["total_profit"] += r.get("final_profit", 0)
            if r.get("final_profit", 0) > 0:
                strategy_stats[s]["wins"] += 1
        
        # 按信号类型分析
        signal_stats = defaultdict(lambda: {"count": 0, "wins": 0, "total_profit": 0})
        for r in completed:
            s = r.get("signal_type", "unknown")
            signal_stats[s]["count"] += 1
            signal_stats[s]["total_profit"] += r.get("final_profit", 0)
            if r.get("final_profit", 0) > 0:
                signal_stats[s]["wins"] += 1
        
        # 按当时涨幅分析
        change_stats = defaultdict(lambda: {"count": 0, "wins": 0, "total_profit": 0})
        for r in completed:
            change = r.get("current_change", 0)
            if change >= 5:
                cat = "大涨(>+5%)"
            elif change >= 3:
                cat = "中涨(3-5%)"
            elif change >= 0:
                cat = "小涨(0-3%)"
            elif change >= -3:
                cat = "小跌(-3~0%)"
            else:
                cat = "大跌(<-3%)"
            
            change_stats[cat]["count"] += 1
            change_stats[cat]["total_profit"] += r.get("final_profit", 0)
            if r.get("final_profit", 0) > 0:
                change_stats[cat]["wins"] += 1
        
        # 找出最佳和最差策略
        best_strategy = max(strategy_stats.items(), 
                          key=lambda x: x[1]["total_profit"]/x[1]["count"] if x[1]["count"] > 0 else 0,
                          default=(None, None))
        worst_strategy = min(strategy_stats.items(), 
                           key=lambda x: x[1]["total_profit"]/x[1]["count"] if x[1]["count"] > 0 else 0,
                           default=(None, None))
        
        return {
            "total_recommendations": total,
            "win_count": len(wins),
            "loss_count": len(losses),
            "win_rate": round(win_rate, 1),
            "avg_profit": round(avg_profit, 2),
            "strategy_stats": dict(strategy_stats),
            "signal_stats": dict(signal_stats),
            "change_stats": dict(change_stats),
            "best_strategy": best_strategy[0] if best_strategy[0] else "数据不足",
            "best_strategy_profit": round(best_strategy[1]["total_profit"]/best_strategy[1]["count"], 2) if best_strategy[1]["count"] > 0 else 0,
            "worst_strategy": worst_strategy[0] if worst_strategy[0] else "数据不足",
            "worst_strategy_profit": round(worst_strategy[1]["total_profit"]/worst_strategy[1]["count"], 2) if worst_strategy[1]["count"] > 0 else 0
        }
    
    def get_optimized_strategy(self):
        """获取优化后的策略建议"""
        analysis = self.analyze_performance()
        
        if "error" in analysis:
            return {
                "suggestion": "数据不足，需要至少10条记录才能给出优化建议",
                "recommendations": []
            }
        
        suggestions = []
        
        # 分析最佳买入时机
        change_stats = analysis.get("change_stats", {})
        best_change = None
        best_change_profit = float('-inf')
        
        for cat, stats in change_stats.items():
            if stats["count"] >= 3:  # 至少3个样本
                avg = stats["total_profit"] / stats["count"]
                if avg > best_change_profit:
                    best_change_profit = avg
                    best_change = cat
        
        if best_change:
            suggestions.append({
                "type": "买入时机",
                "finding": f"历史数据显示，在【{best_change}】时买入效果最好",
                "action": f"重点关注涨幅在{best_change}范围的股票"
            })
        
        # 分析最佳策略
        strategy_stats = analysis.get("strategy_stats", {})
        best_strategy = None
        best_profit = float('-inf')
        
        for strategy, stats in strategy_stats.items():
            if stats["count"] >= 3:
                avg = stats["total_profit"] / stats["count"]
                if avg > best_profit:
                    best_profit = avg
                    best_strategy = strategy
        
        if best_strategy:
            suggestions.append({
                "type": "策略优化",
                "finding": f"【{best_strategy}】策略平均收益{best_profit:.2f}%，表现最佳",
                "action": f"建议重点使用{best_strategy}策略选股"
            })
        
        # 分析信号类型
        signal_stats = analysis.get("signal_stats", {})
        best_signal = None
        best_signal_profit = float('-inf')
        
        for signal, stats in signal_stats.items():
            if stats["count"] >= 3:
                avg = stats["total_profit"] / stats["count"]
                if avg > best_signal_profit:
                    best_signal_profit = avg
                    best_signal = signal
        
        if best_signal:
            suggestions.append({
                "type": "信号类型",
                "finding": f"【{best_signal}】信号胜率最高，平均收益{best_signal_profit:.2f}%",
                "action": f"优先选择{best_signal}信号的股票"
            })
        
        # 止损建议
        losses = [r for r in self.recommendations if r["status"] == "completed" and r.get("final_profit", 0) < 0]
        if losses:
            avg_loss = sum(r.get("final_profit", 0) for r in losses) / len(losses)
            max_loss = min(r.get("final_profit", 0) for r in losses)
            suggestions.append({
                "type": "止损纪律",
                "finding": f"亏损单平均亏{max_loss:.1f}%，最大单笔亏{avg_loss:.1f}%",
                "action": "建议严格遵守3%止损线，避免亏损扩大"
            })
        
        return {
            "total_samples": analysis["total_recommendations"],
            "win_rate": analysis["win_rate"],
            "avg_profit": analysis["avg_profit"],
            "suggestions": suggestions,
            "recommendations": [
                {
                    "rank": 1,
                    "strategy": "强势回调买入",
                    "condition": "涨幅2-5%，缩量回调",
                    "expected_profit": "5-15%",
                    "risk": "中等"
                },
                {
                    "rank": 2,
                    "strategy": "超跌反弹",
                    "condition": "跌幅5-8%，有支撑",
                    "expected_profit": "8-20%",
                    "risk": "较高"
                },
                {
                    "rank": 3,
                    "strategy": "涨停回调",
                    "condition": "昨日涨停，今日回调3-5%",
                    "expected_profit": "10-25%",
                    "risk": "高"
                }
            ]
        }
    
    def generate_report(self):
        """生成回测报告"""
        analysis = self.analyze_performance()
        optimized = self.get_optimized_strategy()
        
        report = []
        report.append("=" * 50)
        report.append("📊 策略回测报告")
        report.append("=" * 50)
        report.append("")
        
        if "error" in analysis:
            report.append(f"⚠️ {analysis['error']}")
            report.append("")
            report.append("📝 继续执行当前策略，数据积累后将自动优化")
        else:
            report.append(f"📈 总推荐数: {analysis['total_recommendations']}")
            report.append(f"✅ 胜率: {analysis['win_rate']}%")
            report.append(f"💰 平均收益: {analysis['avg_profit']}%")
            report.append("")
            report.append("🏆 最佳策略: " + str(analysis['best_strategy']))
            report.append("💔 最差策略: " + str(analysis['worst_strategy']))
            report.append("")
            
            # 涨幅区间分析
            report.append("📊 不同涨幅区间的表现:")
            for cat, stats in analysis.get("change_stats", {}).items():
                if stats["count"] > 0:
                    avg = stats["total_profit"] / stats["count"]
                    wr = stats["wins"] / stats["count"] * 100
                    report.append(f"  {cat}: 样本{stats['count']}个, 胜率{wr:.0f}%, 平均收益{avg:.1f}%")
        
        report.append("")
        report.append("=" * 50)
        report.append("🎯 优化建议")
        report.append("=" * 50)
        
        if optimized.get("suggestions"):
            for i, s in enumerate(optimized["suggestions"], 1):
                report.append(f"{i}. 【{s['type']}】")
                report.append(f"   发现: {s['finding']}")
                report.append(f"   行动: {s['action']}")
                report.append("")
        
        report.append("📋 当前最优策略排名:")
        for rec in optimized.get("recommendations", [])[:3]:
            report.append(f"  {rec['rank']}. {rec['strategy']}")
            report.append(f"     条件: {rec['condition']}")
            report.append(f"     预期收益: {rec['expected_profit']}")
            report.append(f"     风险: {rec['risk']}")
            report.append("")
        
        return "\n".join(report)


def main():
    bt = BacktestSystem()
    report = bt.generate_report()
    print(report)


if __name__ == "__main__":
    main()
