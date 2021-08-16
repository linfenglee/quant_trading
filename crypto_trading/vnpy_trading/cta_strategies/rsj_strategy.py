from typing import Dict
from datetime import time
import numpy as np
from vnpy.app.cta_strategy import (
    CtaTemplate,
    CtaEngine,
    BarGenerator,
    ArrayManager,
    OrderData,
    TradeData,
    StopOrder
)
from vnpy.trader.object import BarData, TickData


class NewArrayManager(ArrayManager):

    def __init__(self, size=100):
        """"""

        super(NewArrayManager, self).__init__(size)

        self.rtn_array: np.ndarray = np.zeros(size)

    def update_bar(self, bar: BarData) -> None:
        """"""

        super(NewArrayManager, self).update_bar(bar)

        if not self.close_array[-2]:
            last_rtn = 0
        else:
            last_rtn = self.close_array[-1] / self.close_array[-2] - 1

        self.rtn_array[:-1] = self.rtn_array[1:]
        self.rtn_array[-1] = last_rtn

    def rsj(self, n: int) -> float:
        """"""

        rtns = self.rtn_array[-n:]
        p_rtns = np.array([r for r in rtns if r > 0])
        n_rtns = np.array([r for r in rtns if r <= 0])

        rv = np.sum(np.square(rtns))
        rv_p = np.sum(np.square(p_rtns))
        rv_n = np.sum(np.square(n_rtns))

        rsj = (rv_p - rv_n) / rv

        return rsj


class RsjStrategy(CtaTemplate):
    """"""

    rsj_window = 12
    price_add = 5
    fixed_size = 1

    rsj_value = 0.0

    parameters = ["rsj_window", "price_add", "fixed_size"]

    variables = ["rsj_value"]

    def __init__(
            self,
            cta_engine: CtaEngine,
            strategy_name: str,
            vt_symbol: str,
            setting: Dict
    ):
        super().__init__(
            cta_engine, strategy_name, vt_symbol, setting
        )

        self.bg = BarGenerator(self.on_bar, 5, self.on_5min_bar)
        self.am = NewArrayManager()

    def on_init(self):
        """"""

        self.write_log("Initialize Strategy")
        self.load_bar(10)

    def on_start(self):
        """"""

        self.write_log("Start Strategy")
        self.put_event()

    def on_stop(self):
        """"""

        self.write_log("Stop Strategy")
        self.put_event()

    def on_tick(self, tick: TickData):
        """"""

        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """"""

        self.bg.update_bar(bar)

    def on_5min_bar(self, bar: BarData):
        """"""

        self.cancel_all()

        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        self.rsj_value = self.am.rsj(self.rsj_window)

        if bar.datetime.time() == time(14, 50):
            if self.rsj_value > 0:
                if self.pos > 0:
                    self.sell(bar.close_price - self.price_add, self.fixed_size)

                self.short(bar.close_price - self.price_add, self.fixed_size)

            elif self.rsj_value < 0:
                if self.pos < 0:
                    self.cover(bar.close_price + self.price_add, self.fixed_size)

                self.buy(bar.close_price + self.price_add, self.fixed_size)

        self.put_event()

    def on_order(self, order: OrderData):
        """"""

        pass

    def on_trade(self, trade: TradeData):
        """"""

        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """"""

        pass

