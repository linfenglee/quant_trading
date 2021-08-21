from typing import List, Dict
from datetime import datetime
import numpy as np

from vnpy.app.portfolio_strategy import StrategyTemplate, StrategyEngine
from vnpy.trader.utility import BarGenerator
from vnpy.trader.object import TickData, BarData


class RotationStrategy(StrategyTemplate):
    """"""

    author = "LarryLee"

    price_add = 5
    ma_interval = 7
    cal_interval = 20
    change_interval = 24
    fixed_capital = 1_000_000

    leg1_symbol = ""
    leg2_symbol = ""
    leg1_return = 0.0
    leg2_return = 0.0
    leg1_std = 0.0
    leg2_std = 0.0
    leg1_ma = 0.0
    leg2_ma = 0.0

    parameters = [
        "price_add", "cal_interval", "change_interval", "fixed_size"
    ]

    variables = [
        "leg1_symbol", "leg2_symbol", "leg1_return", "leg2_return",
        "leg1_std", "leg2_std", "leg1_ma", "leg2_ma"
    ]

    def __init__(
            self,
            strategy_engine: StrategyEngine,
            strategy_name: str,
            vt_symbols: List[str],
            setting: Dict
    ):
        """"""

        super(RotationStrategy, self).__init__(
            strategy_engine, strategy_name, vt_symbols, setting
        )

        self.bgs: Dict[str, BarGenerator] = {}
        self.targets: Dict[str, float] = {}
        self.last_tick_time: datetime = None

        self.return_spread = 0.0
        self.leg1_array: np.array = np.zeros(self.cal_interval)
        self.leg2_array: np.array = np.zeros(self.cal_interval)

        self.leg1_symbol, self.leg2_symbol = vt_symbols

    def on_init(self) -> None:
        """"""

        self.write_log("Initialize Strategy")

        self.load_bars(self.cal_interval)

    def on_start(self) -> None:
        """"""

        self.write_log("Start Strategy")

    def on_stop(self) -> None:
        """"""

        self.write_log("Stop Strategy")

    def on_tick(self, tick: TickData) -> None:
        """"""

        if (
            self.last_tick_time
            and self.last_tick_time.hour != tick.datetime.hour
        ):
            bars = {}
            for vt_symbol, bg in self.bgs.items():
                bars[vt_symbol] = bg.generate()
            self.on_bars(bars)

        bg: BarGenerator = self.bgs[tick.vt_symbol]
        bg.update_tick(tick)

        self.last_tick_time = tick.datetime

    def on_bars(self, bars: Dict[str, BarData]) -> None:
        """"""

        self.cancel_all()

        if self.leg1_symbol not in bars or self.leg2_symbol not in bars:
            return

        leg1_bar = bars[self.leg1_symbol]
        leg2_bar = bars[self.leg2_symbol]

        if (leg1_bar.datetime.hour + 1) % self.change_interval:
            return

        leg1_price, leg2_price = leg1_bar.close_price, leg2_bar.close_price
        self.leg1_array[:-1] = self.leg1_array[1:]
        self.leg1_array[-1] = leg1_price
        self.leg2_array[:-1] = self.leg2_array[1:]
        self.leg2_array[-1] = leg2_price

        if not self.leg1_array[0] or not self.leg2_array[0]:
            return

        self.leg1_ma = self.leg1_array[-self.ma_interval:].mean()
        self.leg2_ma = self.leg2_array[-self.ma_interval:].mean()

        self.leg1_std = np.sqrt(self.cal_interval) * np.diff(self.leg1_array).std()
        self.leg2_std = np.sqrt(self.cal_interval) * np.diff(self.leg2_array).std()

        # self.leg1_return = (self.leg1_array[-1] / self.leg1_array[0] - 1) / self.leg1_std
        # self.leg2_return = (self.leg2_array[-1] / self.leg2_array[0] - 1) / self.leg2_std

        self.leg1_return = self.leg1_array[-1] / self.leg1_array[0] - 1
        self.leg2_return = self.leg2_array[-1] / self.leg2_array[0] - 1

        if self.leg1_return < 0 and self.leg2_return < 0:
            self.targets[self.leg1_symbol] = 0
            self.targets[self.leg2_symbol] = 0

        else:
            if self.leg1_return > self.leg2_return:
                if self.leg1_array[-1] >= self.leg1_ma:
                    self.targets[self.leg1_symbol] = int(self.fixed_capital / leg1_bar.close_price)
                    self.targets[self.leg2_symbol] = 0
                else:
                    self.targets[self.leg1_symbol] = 0
                    self.targets[self.leg2_symbol] = 0
            elif self.leg1_return < self.leg2_return:
                if self.leg2_array[-1] >= self.leg2_ma:
                    self.targets[self.leg1_symbol] = 0
                    self.targets[self.leg2_symbol] = int(self.fixed_capital / leg2_bar.close_price)
                else:
                    self.targets[self.leg1_symbol] = 0
                    self.targets[self.leg2_symbol] = 0
            else:
                self.targets[self.leg1_symbol] = 0
                self.targets[self.leg2_symbol] = 0

        for vt_symbol in self.vt_symbols:
            target_pos = self.targets[vt_symbol]
            current_pos = self.get_pos(vt_symbol)

            pos_diff = target_pos - current_pos
            volume = abs(pos_diff)
            bar = bars[vt_symbol]

            if pos_diff > 0:
                price = bar.close_price + self.price_add

                if current_pos < 0:
                    self.cover(vt_symbol, price, volume)
                else:
                    self.buy(vt_symbol, price, volume)
            elif pos_diff < 0:
                price = bar.close_price - self.price_add

                if current_pos > 0:
                    self.sell(vt_symbol, price, volume)
                else:
                    self.short(vt_symbol, price, volume)

        self.put_event()





