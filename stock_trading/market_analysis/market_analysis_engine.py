import json
from datetime import datetime
import numpy as np
import pandas as pd
import tushare as ts
import plotly
from plotly.subplots import make_subplots
import plotly.graph_objs as go
import akshare as ak


LIMIT_DATE = datetime(2020, 1, 6)


class MarketAnalysisEngine(object):
    """"""

    def __init__(self, date: datetime):
        """"""

        self.pro = self.init_ts()
        self.dts = self.get_trade_dates(date)
        self.dt = self.dts[-1]

    @staticmethod
    def init_ts():
        """"""

        with open("../../data_key.json") as f:
            data_key = json.load(f)

        pro = ts.pro_api(data_key["tushare"]["token"])

        return pro

    def get_trade_dates(self, date: datetime):
        """"""

        end_date = date.strftime("%Y%m%d")

        date_df = self.pro.trade_cal(exchange="", end_date=end_date)

        trade_df = date_df[date_df["is_open"] == 1]
        trade_dates = pd.to_datetime(trade_df["cal_date"]).to_numpy()

        return trade_dates

    @staticmethod
    def limit_industry_plot(
            str_date: str, up_series: pd.Series, down_series: pd.Series
    ):
        """"""

        subtitle1 = f"Limit-Up Industry Analysis ({str_date})"
        subtitle2 = f"Limit-Down Industry Analysis ({str_date})"
        fig = make_subplots(rows=1, cols=2, subplot_titles=(subtitle1, subtitle2))

        trace_up = go.Bar(
            x=up_series.index, y=up_series.values,
            name="Limit-Up: Industry"
        )
        trace_down = go.Bar(
            x=down_series.index, y=down_series.values,
            name="Limit-Down: Industry"
        )

        fig.add_traces([trace_up], rows=1, cols=1)
        fig.add_traces([trace_down], rows=1, cols=2)
        plotly.offline.plot(fig, filename="industry_analysis.html")

    def limit_industry_analysis(self):
        """"""

        str_dt = pd.to_datetime(self.dt).strftime("%Y%m%d")

        limit_up_df = ak.stock_em_zt_pool(date=str_dt)
        up_series = limit_up_df.groupby("所属行业")["代码"].count()
        up_series.sort_values(ascending=False, inplace=True)

        limit_down_df = ak.stock_em_zt_pool_dtgc(date=str_dt)
        down_series = limit_down_df.groupby("所属行业")["代码"].count()
        down_series.sort_values(ascending=False, inplace=True)

        self.limit_industry_plot(str_dt, up_series, down_series)

    @staticmethod
    def limit_up_con_plot(df: pd.DataFrame) -> None:
        """"""

        trace1 = go.Scatter(
            x=df.index, y=df["con"], mode="lines",
            name="Limit Up Continuity"
        )
        trace2 = go.Scatter(
            x=df.index, y=df["trade_con"], mode="lines",
            name="Limit Up Tradable Continuity"
        )
        layout = go.Layout(
            legend={"x": 1, "y": 1},
            title="Limit Up Continuity Analysis"
        )
        fig = go.Figure(data=[trace1, trace2], layout=layout)

        plotly.offline.plot(fig, filename="luc_analysis.html")

    def limit_up_con_analysis(self):
        """"""

        limit_dts = self.dts[pd.to_datetime(self.dts) >= LIMIT_DATE]

        pre_lus = None
        df = pd.DataFrame(columns=["con", "trade_con"])
        for i in range(len(limit_dts) - 1):

            pre_dt, cur_dt = limit_dts[i], limit_dts[i+1]
            str_cur_dt = pd.to_datetime(cur_dt).strftime("%Y%m%d")

            try:
                if pre_lus is None:
                    str_pre_dt = pd.to_datetime(pre_dt).strftime("%Y%m%d")
                    pre_df = ak.stock_em_zt_pool(date=str_pre_dt)
                    pre_lus = pre_df["代码"].to_numpy()
                up_df = ak.stock_em_zt_pool(date=str_cur_dt)
                cur_lus = up_df["代码"].to_numpy()
                up_df["首次封板时间"] = up_df["首次封板时间"].astype("int")
                cur_lus_trade = up_df.loc[up_df["首次封板时间"] > 93000]["代码"].to_numpy()
                if len(pre_lus) == 0 or len(cur_lus) == 0:
                    df.loc[cur_dt] = [0, 0]
                else:
                    success = np.intersect1d(pre_lus, cur_lus)
                    trade_success = np.intersect1d(pre_lus, cur_lus_trade)
                    con = len(success) / len(pre_lus)
                    con_trade = len(trade_success) / len(pre_lus)
                    df.loc[cur_dt] = [con, con_trade]

                pre_lus = cur_lus

            except TypeError:
                print(f"no record for {cur_dt}")
                continue

        df.to_csv("lu_con.csv")
        # df.index = pd.to_datetime(df.index)

        self.limit_up_con_plot(df=df)

    def lhb_analysis(self):
        """"""

        pass

    def money_flow_analysis(self):
        """"""

        pass

    def institute_analysis(self):
        """"""

        pass


if __name__ == "__main__":
    """"""

    dt = datetime.now()
    engine = MarketAnalysisEngine(dt)

    # engine.limit_industry_analysis()
    engine.limit_up_con_analysis()