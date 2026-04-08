"""全市场扫描器 - 激进资金专用"""
import requests
import time
from datetime import datetime
from typing import List, Dict, Optional

class MarketScanner:
    """全市场扫描器 - 激进资金选股"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "http://quote.eastmoney.com/"
        }
        self.cache = {}
        self.cache_time = {}
        self.cache_ttl = 60

    def _get_cached(self, key: str) -> Optional[List]:
        if key in self.cache and key in self.cache_time:
            if time.time() - self.cache_time[key] < self.cache_ttl:
                return self.cache[key]
        return None

    def _set_cache(self, key: str, data: List):
        self.cache[key] = data
        self.cache_time[key] = time.time()

    def get_rising_stocks(self, limit: int = 50) -> List[Dict]:
        """获取今日涨幅榜"""
        cache_key = f"rising_{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": 1,
                "pz": limit,
                "po": 1,
                "np": 1,
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
                "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18",
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            stocks = []
            if data.get("data") and data["data"].get("diff"):
                for item in data["data"]["diff"]:
                    name = item.get("f14", "")
                    # 过滤新股和ST股票 (N=新股, C=科创板新股, ST=特别处理)
                    if name.startswith("N") or name.startswith("C") or name.startswith("ST") or "*ST" in name:
                        continue
                    stocks.append({
                        "code": str(item.get("f12", "")),
                        "name": name,
                        "price": item.get("f2", 0),
                        "change_pct": item.get("f3", 0),
                        "volume": item.get("f5", 0),
                        "turnover": item.get("f6", 0),
                        "amplitude": item.get("f7", 0),
                        "high": item.get("f15", 0),
                        "low": item.get("f16", 0),
                        "open": item.get("f17", 0),
                        "yesterday_close": item.get("f18", 0),
                    })

            self._set_cache(cache_key, stocks)
            return stocks
        except Exception as e:
            print(f"[扫描器] 获取涨幅榜失败: {e}")
            return []

    def get_amplitude_stocks(self, limit: int = 50) -> List[Dict]:
        """获取今日振幅榜"""
        cache_key = f"amplitude_{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": 1,
                "pz": limit,
                "po": 1,
                "np": 1,
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": 2,
                "invt": 2,
                "fid": "f7",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                "fields": "f1,f2,f3,f4,f5,f6,f7,f12,f14,f15,f16,f17,f18",
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            stocks = []
            if data.get("data") and data["data"].get("diff"):
                for item in data["data"]["diff"]:
                    name = item.get("f14", "")
                    if name.startswith("N") or name.startswith("C") or name.startswith("ST") or "*ST" in name:
                        continue
                    stocks.append({
                        "code": str(item.get("f12", "")),
                        "name": name,
                        "price": item.get("f2", 0),
                        "change_pct": item.get("f3", 0),
                        "amplitude": item.get("f7", 0),
                        "volume": item.get("f5", 0),
                        "high": item.get("f15", 0),
                        "low": item.get("f16", 0),
                    })

            self._set_cache(cache_key, stocks)
            return stocks
        except Exception as e:
            print(f"[扫描器] 获取振幅榜失败: {e}")
            return []

    def get_turnover_stocks(self, limit: int = 50) -> List[Dict]:
        """获取换手率榜"""
        cache_key = f"turnover_{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": 1,
                "pz": limit,
                "po": 1,
                "np": 1,
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": 2,
                "invt": 2,
                "fid": "f8",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                "fields": "f1,f2,f3,f5,f6,f8,f12,f14,f15,f16",
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            stocks = []
            if data.get("data") and data["data"].get("diff"):
                for item in data["data"]["diff"]:
                    name = item.get("f14", "")
                    if name.startswith("N") or name.startswith("C") or name.startswith("ST") or "*ST" in name:
                        continue
                    stocks.append({
                        "code": str(item.get("f12", "")),
                        "name": name,
                        "price": item.get("f2", 0),
                        "change_pct": item.get("f3", 0),
                        "turnover_rate": item.get("f8", 0),
                        "volume": item.get("f5", 0),
                        "amount": item.get("f6", 0),
                    })

            self._set_cache(cache_key, stocks)
            return stocks
        except Exception as e:
            print(f"[扫描器] 获取换手率榜失败: {e}")
            return []

    def get_tencent_quote(self, code: str) -> Optional[Dict]:
        """获取腾讯实时行情"""
        try:
            market = "sh" if code.startswith("6") else "sz"
            url = f"https://qt.gtimg.cn/q={market}{code}"
            resp = requests.get(url, timeout=5)
            resp.encoding = 'gbk'
            data = resp.text
            parts = data.split('~')

            if len(parts) > 34:
                return {
                    "code": code,
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

    def scan_aggressive_targets(self, market_status: str = "震荡") -> List[Dict]:
        """扫描激进标的"""
        print(f"[扫描器] 开始扫描激进标的，市场环境: {market_status}")

        all_candidates = []

        print("[扫描器] 获取涨幅榜...")
        rising = self.get_rising_stocks(50)
        print(f"[扫描器] 获取到 {len(rising)} 只涨幅股")

        print("[扫描器] 获取振幅榜...")
        amplitude = self.get_amplitude_stocks(50)
        print(f"[扫描器] 获取到 {len(amplitude)} 只振幅股")

        print("[扫描器] 获取换手率榜...")
        turnover = self.get_turnover_stocks(50)
        print(f"[扫描器] 获取到 {len(turnover)} 只换手股")

        if market_status == "强势":
            print("[扫描器] 强势市场策略: 追强势股")
            for s in rising:
                if 3 <= s["change_pct"] < 9.9:
                    s["strategy"] = "强势追涨"
                    s["score"] = 80 + s["change_pct"] * 5
                    s["reason"] = f"强势市场涨幅{s['change_pct']:.1f}%"
                    all_candidates.append(s)

            for s in amplitude[:20]:
                if s["change_pct"] > 2 and s.get("amplitude", 0) > 5:
                    s["strategy"] = "强势波段"
                    s["score"] = 70 + s["change_pct"] * 3
                    s["reason"] = f"振幅{s.get('amplitude', 0):.1f}%的活跃股"
                    all_candidates.append(s)

        elif market_status == "弱势":
            print("[扫描器] 弱势市场策略: 找超跌机会")
            for s in rising:
                if s["change_pct"] <= -5:
                    s["strategy"] = "超跌反弹"
                    s["score"] = 70 + abs(s["change_pct"]) * 3
                    s["reason"] = f"超跌反弹跌幅{s['change_pct']:.1f}%"
                    all_candidates.append(s)

            for s in turnover[:30]:
                if -3 <= s["change_pct"] < 0:
                    s["strategy"] = "缩量等待"
                    s["score"] = 50 + abs(s["change_pct"]) * 5
                    s["reason"] = f"换手率{s.get('turnover_rate', 0):.1f}%关注"
                    all_candidates.append(s)

        elif market_status in ["震荡", "平稳"]:
            print("[扫描器] 震荡市场策略: 做差价机会")
            for s in amplitude[:30]:
                if s.get("amplitude", 0) > 5:
                    amp = s.get("amplitude", 0)
                    s["strategy"] = "震荡做T"
                    s["score"] = 60 + amp
                    s["reason"] = f"振幅{amp:.1f}%可做T"
                    all_candidates.append(s)

            for s in turnover[:30]:
                if 3 <= s.get("turnover_rate", 0) <= 20:
                    s["strategy"] = "资金关注"
                    s["score"] = 55 + s.get("turnover_rate", 0) * 2
                    s["reason"] = f"换手率{s.get('turnover_rate', 0):.1f}%活跃"
                    all_candidates.append(s)

            for s in rising:
                if 2 <= s["change_pct"] <= 5:
                    s["strategy"] = "震荡追涨"
                    s["score"] = 50 + s["change_pct"] * 5
                    s["reason"] = f"温和上涨{s['change_pct']:.1f}%"
                    all_candidates.append(s)

        # 去重
        seen = set()
        unique_candidates = []
        for s in all_candidates:
            key = s["code"]
            if key not in seen:
                seen.add(key)
                unique_candidates.append(s)

        unique_candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        filtered = [s for s in unique_candidates if s.get("score", 0) >= 50]

        # 验证数据
        print(f"[扫描器] 验证 {len(filtered[:10])} 只候选股票...")
        validated = []
        for s in filtered[:10]:
            detail = self.get_tencent_quote(s["code"])
            if detail:
                s.update(detail)
                change = detail.get("change_pct", s.get("change_pct", 0))
                s["change_pct"] = change
                s["score"] = s.get("score", 50) + change * 2 if change > 0 else s.get("score", 50)
                validated.append(s)
            else:
                validated.append(s)
            time.sleep(0.1)

        validated.sort(key=lambda x: x.get("score", 0), reverse=True)
        print(f"[扫描器] 扫描完成，找到 {len(validated)} 只激进标的")
        return validated[:5]

    def format_recommendation(self, stock: Dict, position: int = 1) -> str:
        """格式化推荐输出"""
        name = stock.get("name", "未知")
        code = stock.get("code", "")
        price = stock.get("price", 0)
        change = stock.get("change_pct", 0)
        strategy = stock.get("strategy", "未知")
        reason = stock.get("reason", "")
        amplitude = stock.get("amplitude", 0)
        turnover_rate = stock.get("turnover_rate", 0)

        if change > 0:
            buy_price = round(price * 0.998, 2)
        else:
            buy_price = round(price * 0.99, 2)

        stop_loss = round(buy_price * 0.97, 2)
        target = round(buy_price * 1.05, 2)
        shares = int(10000 / buy_price) if buy_price > 0 else 0

        if change > 9.5:
            action = "⚠️ 接近涨停，不建议追"
            action_detail = "等明天看是否继续强势"
        elif change > 6:
            action = "🟠 大涨，需谨慎"
            action_detail = f"可以轻仓1000股试试"
            shares = min(shares, 1000)
        elif change > 0:
            action = "✅ 温和上涨，可以买"
            action_detail = f"建议买{shares}股"
        elif change > -3:
            action = "🔵 小跌，可以关注"
            action_detail = f"等跌更多或反弹再买"
        elif change > -6:
            action = "🟣 超跌，可以买入"
            action_detail = f"建议买{shares}股抢反弹"
        else:
            action = "🔴 大跌，注意风险！"
            action_detail = f"建议最多买{int(shares/2)}股，止损要严"

        lines = [
            f"#{position} {name}({code})",
            f"现价: {price} | 涨幅: {change:+.1f}% | 振幅: {amplitude:.1f}%",
            f"换手: {turnover_rate:.1f}% | 策略: {strategy}",
            f"→ {action}",
            f"  买价: {buy_price} | 止损: {stop_loss} | 目标: {target}",
            f"  {action_detail}",
        ]

        return "\n".join(lines)
