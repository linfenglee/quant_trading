import json
from typing import Tuple, List
from datetime import datetime, timedelta
import pandas as pd
import tushare as ts
import plotly
import plotly.graph_objs as go


class NorthFlowEngine(object):
    """"""

    def __init__(
            self, start_date: datetime, end_date: datetime
    ):
        """"""

        self.start_date = start_date
        self.end_date = end_date
        self.pro = self.init_ts()

    @staticmethod
    def init_ts():
        """"""

        with open("../../data_key.json") as f:
            data_key = json.load(f)

        pro = ts.pro_api(data_key["tushare"]["token"])

        return pro

    def get_trade_dates(self):
        """"""

        hgt_date = self.start_date.strftime("%Y%m%d")
        end_date = self.end_date.strftime("%Y%m%d")

        date_df = self.pro.trade_cal(
            exchange="", start_date=hgt_date, end_date=end_date
        )

        trade_df = date_df[date_df["is_open"] == 1]
        trade_dates = pd.to_datetime(trade_df["cal_date"]).to_numpy()

        return trade_dates

    def get_hsgt_stocks(self, trade_date: datetime) -> Tuple:
        """"""
        str_dt = pd.to_datetime(trade_date).strftime("%Y%m%d")
        h_stocks = self.pro.hsgt_top10(trade_date=str_dt, market_type="1")
        s_stocks = self.pro.hsgt_top10(trade_date=str_dt, market_type="3")
        # hs_stocks = self.pro.hsgt_top10(trade_date=trade_date)

        return h_stocks, s_stocks

    @staticmethod
    def north_flow_plot(
            trade_dates: List, h_series: pd.Series, s_series: pd.Series) -> None:
        """"""

        start_trade = trade_dates[0]
        end_trade = trade_dates[-1]
        trade_length = len(trade_dates)
        h_trace = go.Bar(
            x=h_series.index, y=h_series.values,
            name="Shanghai"
        )
        s_trace = go.Bar(
            x=s_series.index, y=s_series.values,
            name="Shenzhen"
        )
        layout = go.Layout(
            legend={"x": 1, "y": 1},
            title=f"North Flow: {start_trade} - {end_trade} ({trade_length} trading days)"
        )
        fig = go.Figure(data=[h_trace, s_trace], layout=layout)

        plotly.offline.plot(fig, filename="north_flow.html")

    def north_flow_main(self) -> Tuple:
        """"""

        trade_dates = self.get_trade_dates()

        dts = []
        h_data, s_data = pd.DataFrame(), pd.DataFrame()
        for trade_date in trade_dates:
            h_df, s_df = self.get_hsgt_stocks(trade_date=trade_date)
            if h_df.empty or s_df.empty:
                continue
            dts.append(pd.to_datetime(trade_date).strftime("%Y-%m-%d"))
            h_data = pd.concat([h_data, h_df], ignore_index=True)
            s_data = pd.concat([s_data, s_df], ignore_index=True)

        h_series = h_data.groupby("name")["net_amount"].sum().sort_values(ascending=False)
        s_series = s_data.groupby("name")["net_amount"].sum().sort_values(ascending=False)

        self.north_flow_plot(dts, h_series, s_series)

        return h_series, s_series


if __name__ == "__main__":
    """"""

    e_date = datetime.now()
    s_date = e_date - timedelta(days=5)
    engine = NorthFlowEngine(s_date, e_date)

    sh_series, sz_series = engine.north_flow_main()

