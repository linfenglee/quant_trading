import json
from typing import Tuple, List
from datetime import datetime, timedelta
import pandas as pd
import tushare as ts
import plotly
from plotly.subplots import make_subplots
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
            trade_dates: List,
            h_net_series: pd.Series, s_net_series: pd.Series,
            h_rel_series: pd.Series, s_rel_series: pd.Series
    ) -> None:
        """"""

        start_trade = trade_dates[0]
        end_trade = trade_dates[-1]
        trade_length = len(trade_dates)

        subtitle1 = f"North Flow Net Amount: {start_trade} - {end_trade} ({trade_length} trading days)"
        subtitle2 = f"North Flow Relative Amount: {start_trade} - {end_trade} ({trade_length} trading days)"
        fig = make_subplots(rows=2, cols=1, subplot_titles=(subtitle1, subtitle2))

        h_net_trace = go.Bar(
            x=h_net_series.index, y=h_net_series.values,
            name="Shanghai"
        )
        s_net_trace = go.Bar(
            x=s_net_series.index, y=s_net_series.values,
            name="Shenzhen"
        )
        h_rel_trace = go.Bar(
            x=h_rel_series.index, y=h_rel_series.values,
            name="Shanghai"
        )
        s_rel_trace = go.Bar(
            x=s_rel_series.index, y=s_rel_series.values,
            name="Shenzhen"
        )
        fig.add_traces([h_net_trace, s_net_trace], rows=1, cols=1)
        fig.add_traces([h_rel_trace, s_rel_trace], rows=2, cols=1)

        plotly.offline.plot(fig, filename="north_flow.html")

    def north_flow_main(self) -> None:
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

        h_net_series = h_data.groupby("name")["net_amount"].sum().sort_values(ascending=False)
        s_net_series = s_data.groupby("name")["net_amount"].sum().sort_values(ascending=False)

        h_sum_series = h_data.groupby("name")["amount"].sum()
        s_sum_series = s_data.groupby("name")["amount"].sum()

        h_rel_series = (h_net_series / h_sum_series).sort_values(ascending=False)
        s_rel_series = (s_net_series / s_sum_series).sort_values(ascending=False)

        self.north_flow_plot(
            dts, h_net_series, s_net_series, h_rel_series, s_rel_series
        )


if __name__ == "__main__":
    """"""

    e_date = datetime.now()
    s_date = e_date - timedelta(days=5)
    engine = NorthFlowEngine(s_date, e_date)

    engine.north_flow_main()

