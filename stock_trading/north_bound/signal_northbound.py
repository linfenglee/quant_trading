import os
from time import sleep
from typing import Tuple
from datetime import datetime, time, timedelta
import pandas as pd
from pandas import DataFrame
import json
import plotly
import plotly.graph_objs as go
import tushare as ts


HGT_DATE = datetime(2014, 11, 17)  # HGT Start Date
SGT_DATE = datetime(2016, 12, 5)   # SGT Start Date

UPDATE_TIME = time(19, 0)


class NorthBound(object):
    """"""

    # os.chdir("./north_bound/")

    def __init__(
            self, start_date=None, end_date=None, query_limit=100
    ):
        """"""

        self.s_date = self.get_start_date(start_date)

        self.e_date = self.get_end_date(end_date)

        self.q_limit = query_limit

        self.pro = self.init_ts()

    @staticmethod
    def get_start_date(start_date) -> datetime:
        """"""

        if start_date is None:
            s_date = HGT_DATE
        else:
            s_date = start_date
        return s_date

    @staticmethod
    def get_end_date(end_date) -> datetime:
        """"""
        if end_date is None:
            if datetime.now().time() <= UPDATE_TIME:
                e_date = datetime.now() - timedelta(days=1)
            else:
                e_date = datetime.now()
        else:
            e_date = end_date

        return e_date

    @staticmethod
    def init_ts():
        """"""

        with open("../../data_key.json") as f:
            data_key = json.load(f)

        pro = ts.pro_api(data_key["tushare"]["token"])

        return pro

    def get_trade_dates(self):
        """"""

        hgt_date = self.s_date.strftime("%Y%m%d")
        end_date = self.e_date.strftime("%Y%m%d")

        date_df = self.pro.trade_cal(
            exchange="", start_date=hgt_date, end_date=end_date
        )

        trade_df = date_df[date_df["is_open"] == 1]
        trade_dates = pd.to_datetime(trade_df["cal_date"]).to_numpy()

        return trade_dates

    def get_index_price(self):
        """"""

        hs300 = self.pro.index_daily(
            ts_code="399300.SZ",
            start_date=HGT_DATE.strftime("%Y%m%d"),
            end_date=self.e_date.strftime("%Y%m%d")
        )
        hs300["trade_date"] = pd.to_datetime(hs300["trade_date"])
        hs300.set_index("trade_date", inplace=True)

        return hs300

    def get_hsgt(self, start_date: str, end_date: str) -> DataFrame:
        """"""

        hsgt = self.pro.moneyflow_hsgt(
            start_date=start_date, end_date=end_date
        )
        hsgt["trade_date"] = pd.to_datetime(hsgt["trade_date"])
        hsgt.set_index("trade_date", inplace=True)

        return hsgt

    def get_one_hsgt(self, trade_date) -> DataFrame:
        """"""

        hsgt = self.pro.moneyflow_hsgt(trade_date=trade_date)
        hsgt["trade_date"] = pd.to_datetime(hsgt["trade_date"])
        hsgt.set_index("trade_date", inplace=True)

        return hsgt

    @staticmethod
    def hsgt_plot(hsgt_df: DataFrame) -> None:
        """"""

        data = []
        for colname in hsgt_df.columns:
            data.append(
                go.Scatter(
                    x=hsgt_df.index, y=hsgt_df[colname],
                    mode="lines", name=colname
                )
            )

        layout = go.Layout(
            legend={"x": 1, "y": 1},
            title="Stock Connection - Money Flow"
        )
        fig = go.Figure(data=data, layout=layout)

        plotly.offline.plot(fig, filename="hsgt_money_flow.html")

    @staticmethod
    def get_record_df():
        """"""

        if os.path.exists("hsgt.csv"):
            df = pd.read_csv("hsgt.csv")
            df["trade_date"] = pd.to_datetime(df["trade_date"])
            df.set_index("trade_date", inplace=True)
        else:
            df = DataFrame()

        return df

    @staticmethod
    def show_progress(count: int, total: int) -> None:
        """"""

        percentage = int(100 * count / total)
        output = "#" * percentage + " " + f"{percentage}%"
        if percentage < 100:
            print(output, end="\r")
        else:
            print(output, end="\n")

    def main_one_record(self) -> Tuple:
        """"""

        df = self.get_record_df()

        trade_dates = self.get_trade_dates()

        hs300 = self.get_index_price()

        if not df.empty:
            trade_dates = trade_dates[trade_dates > df.index[-1]]

        count = 0
        total = len(trade_dates)
        error_dates = []
        for trade_date in trade_dates:

            hsgt = self.get_one_hsgt(
                pd.to_datetime(trade_date).strftime("%Y%m%d")
            )
            if hsgt.empty:
                error_dates.append(trade_date)
            df = pd.concat([df, hsgt])
            count += 1
            self.show_progress(count, total)

            sleep(60 / self.q_limit)

        self.hsgt_plot(df)

        if error_dates:
            print(error_dates)

        df.to_csv("hsgt.csv")
        hs300.to_csv("hs300.csv")

        return df, error_dates

    def main_many_records(self):
        """"""

        df = self.get_record_df()

        trade_dates = self.get_trade_dates()

        if not df.empty:
            trade_dates = trade_dates[trade_dates > df.index[-1]]

        count = 0
        total = len(trade_dates)
        # q, r = total // self.q_limit, total % self.q_limit
        for trade_date in trade_dates:
            hsgt = self.get_one_hsgt(trade_date)
            df = pd.concat([df, hsgt])
            count += 1
            self.show_progress(count, total)

            sleep(60 / self.q_limit)

        self.hsgt_plot(df)

        hs300 = self.get_index_price()
        df["close"] = hs300["close"]
        df["open"] = hs300["open"]
        df.to_csv("hsgt.csv")

        return hs300, df


if __name__ == "__main__":
    """"""

    sd = None
    ed = None

    north_bound = NorthBound(start_date=sd, end_date=ed)

    hs_df, errors = north_bound.main_one_record()