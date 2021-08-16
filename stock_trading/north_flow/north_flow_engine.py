import json
from datetime import datetime, timedelta
import pandas as pd
import tushare as ts


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

    def get_hsgt_stocks(self, trade_date):
        """"""

        # h_stocks = self.pro.hsgt_top10(trade_date=trade_date, market_type="1")
        # s_stocks = self.pro.hsgt_top10(trade_date=trade_date, market_type="3")
        # hs_stocks = pd.concat([h_stocks, s_stocks], ignore_index=True)

        hs_stocks = self.pro.hsgt_top10(trade_date=trade_date)

        return hs_stocks

    def north_flow_main(self):
        """"""

        trade_dates = self.get_trade_dates()

        for trade_date in trade_dates:
            hs_df = self.get_hsgt_stocks(trade_date=trade_date)


if __name__ == "__main__":

    pass

