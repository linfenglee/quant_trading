import os
from typing import Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import json
import tushare as ts

import plotly
import plotly.graph_objs as go


class NorthBoundEngine(object):
    """"""

    # os.chdir("./north_bound/")

    def __init__(self, start_date, end_date, interval=365):
        """"""

        self.s_date = start_date
        self.e_date = end_date
        self.interval = interval

        self.pro = self.init_ts()

        hs_df = self.init_hsgt()
        hs300 = self.init_hs300()

        self.df = pd.concat([hs300, hs_df], axis=1)

    def __str__(self):
        """"""

        pass

    @staticmethod
    def init_ts():
        """"""

        with open("../../data_key.json") as f:
            data_key = json.load(f)

        pro = ts.pro_api(data_key["tushare"]["token"])

        return pro

    @staticmethod
    def init_hsgt():
        """"""

        hs_df = pd.read_csv("hsgt.csv")
        hs_df["trade_date"] = pd.to_datetime(hs_df["trade_date"])
        hs_df.set_index("trade_date", inplace=True)

        return hs_df

    @staticmethod
    def init_hs300():
        """"""

        hs300 = pd.read_csv("hs300.csv")
        hs300["trade_date"] = pd.to_datetime(hs300["trade_date"])
        hs300.set_index("trade_date", inplace=True)

        return hs300

    def get_trade_dates(self):
        """"""

        date_df = self.pro.trade_cal(
            exchange="",
            start_date=self.s_date.strftime("%Y%m%d"),
            end_date=self.e_date.strftime("%Y%m%d")
        )

        trade_df = date_df[date_df["is_open"] == 1]
        trade_dates = pd.to_datetime(trade_df["cal_date"]).to_numpy()

        return trade_dates

    def north_bound_signal(self, trade_date: datetime) -> Tuple:
        """"""

        cal_date = pd.to_datetime(trade_date) - timedelta(days=self.interval)

        cal_data = self.df[
            (self.df.index >= cal_date) & (self.df.index < trade_date)
        ]["north_money"]

        br, sr = cal_data.quantile(3/4), cal_data.quantile(1/4)

        return br, sr

    def backtest_plot(self, df: pd.DataFrame) -> None:
        """"""

        df["return_close"] = (df["close"].shift(-1) - df["close"]) / df["close"]
        df["return_open"] = (df["open"].shift(-1) - df["open"]) / df["open"]
        df.dropna(inplace=True)
        df["wealth1"] = np.cumprod(df["return_open"] * df["position"].shift() + 1)
        df["wealth2"] = np.cumprod(df["return_close"] + 1)

        trace_nm = go.Scatter(
            x=self.df.index, y=df["wealth1"],
            mode="lines", name="North Money Strategy"
        )

        trace_bh = go.Scatter(
            x=self.df.index, y=df["wealth2"],
            mode="lines", name="Buy & Hold Strategy"
        )

        layout = go.Layout(
            legend={"x": 1, "y": 1},
            title="North Money Strategy v.s. Buy & Hold Strategy"
        )

        fig = go.Figure(data=[trace_nm, trace_bh], layout=layout)

        plotly.offline.plot(fig, filename='strategy_backtest.html')

    def main(self):
        """"""

        trade_dates = self.get_trade_dates()

        pre_signal = 0
        signals = pd.DataFrame(columns=["close", "open", "position"])
        for trade_date in trade_dates:

            br, sr = self.north_bound_signal(trade_date)

            north_money = self.df.loc[trade_date, "north_money"]
            open_price = self.df.loc[trade_date, "open"]
            close_price = self.df.loc[trade_date, "close"]
            if north_money > br:
                position = 1
                pre_signal = 1
            elif north_money < sr:
                position = 0
                pre_signal = 0
            else:  # there exists nan or [sr, br]
                position = pre_signal
            signals.loc[trade_date] = [close_price, open_price, position]

        self.backtest_plot(signals)

        return signals


if __name__ == "__main__":
    """"""

    sd = datetime(2015, 11, 17)
    ed = datetime(2021, 7, 1)

    # print(os.getcwd())

    engine = NorthBoundEngine(start_date=sd, end_date=ed)

    signal_df = engine.main()

