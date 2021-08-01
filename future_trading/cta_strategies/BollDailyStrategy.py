from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)
import talib as ta
import matplotlib.pyplot as plt
import pandas as pd
from vnpy.trader.constant import Exchange, Interval


class BollDailyStrategy(CtaTemplate):
    """"""
    MaxDB = 22
    HLlength = 27
    Length = 18
    Offset = 2

    parameters = ['MaxDB', 'HLlength', 'Length', 'Offset']
    variables = []

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.ContractUint = 10000  # setting['size']
        self.bg = BarGenerator(self.on_bar, 24, self.on_day_bar, Interval.HOUR)
        self.am = ArrayManager()

        self.am_day = ArrayManager()
        self.last_trade_id = 0
        self.MidLine = [0]
        self.UpLine = [0]
        self.DownLine = [0]
        self.MidLinebuycon = 0
        self.MidLinesellcon = 0
        self.buycon = 0
        self.sellcon = 0
        self.lots = 0
        self.H_line = 0
        self.L_line = 0

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")
        self.load_bar(10)

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.write_log("策略启动")

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.bg.update_bar(bar)

        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        if self.MidLine[-1] == 0:
            return
        else:
            # 出场条件
            self.MidLinebuycon = bar.close_price > self.MidLine[-1]
            self.MidLinesellcon = bar.close_price < self.MidLine[-1]
            # 进场条件
            self.buycon = (bar.close_price >= self.UpLine[-1]) and (am.high_array[-2] < self.UpLine[-2]) and (
                        self.UpLine[-1] >= self.H_line)
            #价格上穿，同时upline突破新高
            self.sellcon = (bar.close_price <= self.DownLine[-1]) and (am.low_array[-2] > self.DownLine[-2]) and (
                        self.DownLine[-1] <= self.L_line)
            #价格下穿，同时downline新低

            if self.pos > 0:
                # 调控仓位
                if self.pos > self.lots:
                    self.sell(bar.close_price - 5, self.pos - self.lots)
                # 中轨平仓
                if bar.low_price <= self.MidLine[-1]:
                    self.sell(min(bar.close_price, self.MidLine[-1]) - 5, self.pos)

            if self.pos < 0:
                # 调控仓位
                if abs(self.pos) > self.lots:
                    self.cover(bar.close_price + 5, abs(self.pos) - self.lots)
                # 中轨平仓
                if bar.high_price >= self.MidLine[-1]:
                    self.cover(max(bar.close_price, self.MidLine[-1]) + 5, abs(self.pos))

            if self.pos == 0:
                if self.buycon and self.MidLinebuycon:
                    self.buy(max(bar.close_price, self.UpLine[-1]) + 5, self.lots)

                if self.sellcon and self.MidLinesellcon:
                    self.short(min(bar.close_price, self.DownLine[-1]) - 5, self.lots)

        self.put_event()

    def on_day_bar(self, bar: BarData):
        """"""
        self.cancel_all()

        am = self.am_day
        am.update_bar(bar)
        if not am.inited:
            return

        RiskRation = self.MaxDB
        AvgTR = am.atr(int(self.Length / 2))
        self.lots = int((RiskRation * 100) / (AvgTR * self.ContractUint))
        # print(self.lots)

        self.MidLine = ta.MA(am.close, self.Length)
        Band = ta.STDDEV(am.high_array, self.Length)
        self.UpLine = self.MidLine + self.Offset * Band
        self.DownLine = self.MidLine - self.Offset * Band

        self.H_line = max(am.high_array[-self.HLlength:])
        self.L_line = min(am.low_array[-self.HLlength:])

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        pass
