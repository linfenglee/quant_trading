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


class OscillatorDriveStrategy(CtaTemplate):
    """"""

    author = "用Python的交易员"

    boll_window = 34
    boll_dev = 2.4
    atr_window = 20
    trading_size = 1
    risk_level = 50
    sl_multiplier = 1.8
    dis_open = 8
    interval = 25

    boll_up = 0
    boll_down = 0
    cci_value = 0
    atr_value = 0
    long_stop = 0
    short_stop = 0
    
    exit_up = 0
    exit_down = 0

    parameters = ["boll_window", "boll_dev", 
                  "dis_open", "interval", "atr_window", 
                  "sl_multiplier"]
    variables = ["boll_up", "boll_down", "atr_value",
                 "intra_trade_high", "intra_trade_low", 
                 "long_stop", "short_stop"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super(OscillatorDriveStrategy, self).__init__(
            cta_engine, strategy_name, vt_symbol, setting
        )

        self.bg = BarGenerator(self.on_bar, self.interval, self.on_xmin_bar)
        self.am = ArrayManager()

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

    def on_xmin_bar(self, bar: BarData):
        """"""
        self.cancel_all()

        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        self.boll_up, self.boll_down = am.boll(self.boll_window, self.boll_dev)

        self.ultosc = am.ultosc()
        buy_dis = 50 + self.dis_open
        sell_dis = 50 - self.dis_open
        self.atr_value = am.atr(self.atr_window)

        if self.pos == 0:
            self.trading_size = max(int(self.risk_level / self.atr_value), 1)
            self.intra_trade_high = bar.high_price
            self.intra_trade_low = bar.low_price

            if self.ultosc > buy_dis:
                self.buy(self.boll_up, self.trading_size, True)
            elif self.ultosc < sell_dis:
                self.short(self.boll_down, self.trading_size, True)

        elif self.pos > 0:
            self.intra_trade_high = max(self.intra_trade_high, bar.high_price)
            self.intra_trade_low = bar.low_price

            self.long_stop = self.intra_trade_high - self.atr_value * self.sl_multiplier
            self.sell(self.long_stop, abs(self.pos), True)

        elif self.pos < 0:
            self.intra_trade_high = bar.high_price
            self.intra_trade_low = min(self.intra_trade_low, bar.low_price)

            self.short_stop = self.intra_trade_low + self.atr_value * self.sl_multiplier
            self.cover(self.short_stop, abs(self.pos), True)

        self.put_event()

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
