def compute(payload):
    """按最新市场日的 30 天窗口、相对绝对涨跌幅和代号打破平局，返回前 top 个房间代号（保持排名）。"""
    market = payload["market"]
    top = payload["top"]
    L = max(row[1] for row in market)
    window = [row for row in market if L - 29 <= row[1] <= L]
    window.sort(key=lambda row: (-abs(row[3] - row[2]) / row[2], row[0]))
    return [row[0] for row in window[:top]]
