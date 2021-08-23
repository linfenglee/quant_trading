import json
from datetime import datetime
import pandas as pd
import tushare as ts
import plotly
from plotly.subplots import make_subplots
import plotly.graph_objs as go
import akshare as ak


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
    engine.limit_industry_analysis()