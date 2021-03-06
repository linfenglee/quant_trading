from typing import Tuple
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np
import tushare as ts

import plotly
from plotly.subplots import make_subplots
import plotly.graph_objs as go


START_DATE = datetime(2005, 1, 4)
DROP_COLS = ["ts_code", "pre_close", "change", "vol", "amount"]
SUBTITLES = (
    "Mean", "Median", "Positive Percentage",
    "Bull Mean", "Bull Median", "Bull Positive Percentage",
    "Bear Mean", "Bear Median", "Bear Positive Percentage"
)


class WeekEffectEngine(object):
    """"""

    def __init__(
            self, index_code: str = "399300.SZ", ma_window: int = 20
    ):
        """"""

        self.pro = self.init_ts()
        self.index_df = self.get_index_df(index_code)
        self.bull_bear_split(ma_window)

    @staticmethod
    def init_ts():
        """"""

        with open("../../data_key.json") as f:
            data_key = json.load(f)

        pro = ts.pro_api(data_key["tushare"]["token"])

        return pro

    def get_index_df(self, index_code: str) -> pd.DataFrame:
        """"""

        start_dt = START_DATE.strftime("%Y%m%d")
        end_dt = datetime.now().strftime("%Y%m%d")
        index_df = self.pro.index_daily(
            ts_code=index_code, start_date=start_dt, end_date=end_dt
        )

        index_df["trade_date"] = pd.to_datetime(index_df["trade_date"])
        index_df["week_day"] = index_df["trade_date"].apply(lambda dt: dt.isoweekday())
        index_df.set_index("trade_date", inplace=True)
        index_df.sort_index(ascending=True, inplace=True)

        index_df["return"] = index_df["close"].shift(-1) / index_df["close"] - 1
        index_df["pos_chg"] = index_df["pct_chg"] > 0
        # index_df["pos_rtn"] = index_df["return"] >= 0
        index_df.drop(columns=DROP_COLS, inplace=True)
        index_df.dropna(inplace=True)

        return index_df

    def bull_bear_split(self, ma_window: int = 20):
        """"""

        self.index_df["ma"] = self.index_df["close"].rolling(ma_window).mean()
        self.index_df.dropna(inplace=True)
        self.index_df["regime"] = (self.index_df["close"] - self.index_df["ma"] > 0)

    @staticmethod
    def calc_statistics(calc_obj, pos_calc_obj) -> Tuple:
        """"""
        mean_series = calc_obj["pct_chg"].mean()
        median_series = calc_obj["pct_chg"].median()
        pos_series = pos_calc_obj["pos_chg"].count() / calc_obj["pct_chg"].count()

        return mean_series, median_series, pos_series

    @staticmethod
    def statistic_plot(
            fig, row_num, mean_series, median_series, pos_series
    ) -> go.Figure:
        """"""

        mean_trace = go.Bar(
            x=mean_series.index, y=mean_series.values
        )
        median_trace = go.Bar(
            x=median_series.index, y=median_series.values
        )
        pos_trace = go.Bar(
            x=pos_series.index, y=pos_series.values
        )

        fig.add_traces([mean_trace], rows=row_num, cols=1)
        fig.add_traces([median_trace], rows=row_num, cols=2)
        fig.add_traces([pos_trace], rows=row_num, cols=3)

        return fig

    def statistic_analysis(self) -> None:
        """"""

        # whole market
        obj = self.index_df.groupby("week_day")
        pos_obj = self.index_df[self.index_df["pos_chg"]].groupby("week_day")
        mean_series, median_series, pos_series = self.calc_statistics(obj, pos_obj)

        # bull market regime
        bull_df = self.index_df[self.index_df["regime"]==True]
        bull_obj = bull_df.groupby("week_day")
        bull_pos_obj = bull_df[bull_df["pos_chg"]].groupby("week_day")
        bull_mean, bull_median, bull_pos = self.calc_statistics(bull_obj, bull_pos_obj)

        # bear market regime
        bear_df = self.index_df[self.index_df["regime"]==False]
        bear_obj = bear_df.groupby("week_day")
        bear_pos_obj = bear_df[bear_df["pos_chg"]].groupby("week_day")
        bear_mean, bear_median, bear_pos = self.calc_statistics(bear_obj, bear_pos_obj)

        fig = make_subplots(rows=3, cols=3, subplot_titles=SUBTITLES)

        fig = self.statistic_plot(
            fig, 1, mean_series, median_series, pos_series
        )
        fig = self.statistic_plot(
            fig, 2, bull_mean, bull_median, bull_pos
        )
        fig = self.statistic_plot(
            fig, 3, bear_mean, bear_median, bear_pos
        )

        plotly.offline.plot(fig, filename="week_effect_statistics.html")

    def analysis(self):
        """"""

        pass

    def wealth_plot(self) -> None:
        """"""

        wealth_trace = go.Scatter(
            x=self.index_df.index, y=self.index_df["wealth"],
            name="Wealth", mode="lines"
        )
        baseline_trace = go.Scatter(
            x=self.index_df.index, y=self.index_df["baseline"],
            name="Baseline", mode="lines"
        )

        layout = go.Layout(
            title="Week Effect Backtesting Result"
        )
        fig = go.Figure(
            data=[wealth_trace, baseline_trace], layout=layout
        )

        plotly.offline.plot(fig, filename="week_effect_backtest.html")

    def back_testing(self) -> None:
        """"""

        dts = self.index_df.index
        position = 0
        ps = []
        for i in range(len(dts)-1):
            cdt, fdt = dts[i], dts[i+1]
            regime = self.index_df.loc[cdt, "regime"]
            fwd = self.index_df.loc[fdt, "week_day"]

            if regime:
                if fwd in [1, 5]:
                    position = 1
                elif fwd in [2, 4]:
                    position = 0
            else:
                if fwd in [2, 3]:
                    position = 1
                elif fwd in [1, 4]:
                    position = 0
                # position = 0

            ps.append(position)

        # flat the position
        ps.append(0)
        self.index_df["position"] = ps

        self.index_df["wealth"] = np.cumprod(
            self.index_df["return"] * self.index_df["position"] + 1
        )
        self.index_df["baseline"] = np.cumprod(self.index_df["return"] + 1)

        self.wealth_plot()

    def get_trade_dates(self):
        """"""

        end_dt = datetime.now().strftime("%Y%m%d")
        start_dt = (datetime.now() - timedelta(days=50)).strftime("%Y%m%d")
        date_df = self.pro.trade_cal(
            exchange="", start_date=start_dt, end_date=end_dt
        )

        trade_df = date_df[date_df["is_open"] == 1]
        trade_dates = pd.to_datetime(trade_df["cal_date"]).to_numpy()

        return trade_dates

    def current_output(self) -> None:
        """"""

        pre_dt, cur_dt = self.index_df.index[-2], self.index_df.index[-1]
        cur_regime = self.index_df.loc[cur_dt, "regime"]
        cur_week_day = cur_dt.isoweekday()
        pre_position = self.index_df.loc[pre_dt, "position"]

        if cur_regime:
            if cur_week_day in [1, 5]:
                cur_position = 1
            elif cur_week_day in [2, 4]:
                cur_position = 0
            else:
                cur_position = pre_position
        else:
            if cur_week_day in [2, 3]:
                cur_position = 1
            elif cur_week_day in [1, 4]:
                cur_position = 0
            else:
                cur_position = pre_position

        str_dt = cur_dt.strftime("%Y-%m-%d")
        hline = "=" * 40 + "\n"
        line1 = f"Date: {str_dt} \t| Week Day: {cur_week_day}\n"
        line2 = f"Bull Regime: {cur_regime} \t| Position: {cur_position}\n"

        output = hline + line1 + line2 + hline
        print(output)


if __name__ == "__main__":
    """"""

    ts_code = "399300.SZ"
    ma_value = 15

    engine = WeekEffectEngine(
        index_code=ts_code, ma_window=ma_value
    )

    # get whole, bull and bear market statistics
    engine.statistic_analysis()

    # back test week effect strategy
    engine.back_testing()

    # output current situation
    engine.current_output()