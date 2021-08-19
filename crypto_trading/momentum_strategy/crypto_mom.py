import sys
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import pandas as pd
import ccxt
import plotly
from plotly.subplots import make_subplots
import plotly.graph_objs as go


class MomEngine(object):
    """"""

    def __init__(
            self,
            exchange: str,
            proxy: bool,
            symbols: List,
            interval: str,
            window: int
    ):
        """"""

        if not self.check_exchange(exchange):
            print(f"{exchange} is not in exchange list.")
            sys.exit()

        self.engine = self.init_engine(exchange, proxy)

        if (
                (not self.check_symbols(symbols)) or
                (not self.check_interval(interval))
        ):
            sys.exit()

        self.symbols = symbols
        self.interval = interval
        self.window = window

    @staticmethod
    def init_engine(exchange: str, proxy: bool):
        """"""

        exec_code = f"ccxt.{exchange}()"
        engine = eval(exec_code)
        if proxy:
            engine.proxies = {
                'http': 'http://127.0.0.1:41091',
                'https': 'https://127.0.0.1:41091',
            }
        return engine

    @staticmethod
    def check_exchange(exchange: str) -> bool:
        """"""

        exchange_list = ccxt.exchanges

        if exchange in exchange_list:
            return True
        else:
            return False

    def check_symbols(self, symbols: List) -> bool:
        """"""

        market_symbols = self.engine.load_markets().keys()

        error_symbols = []
        for symbol in symbols:
            if symbol not in market_symbols:
                error_symbols.append(symbol)

        if error_symbols:
            print(f"{error_symbols} not in market symbols")
            return False
        else:
            return True

    def check_interval(self, interval: str) -> bool:
        """"""

        if interval in self.engine.timeframes:
            return True
        else:
            print(f"{interval} not in the timeframes")
            return False

    def split_interval(self) -> Tuple:
        """"""

        scale = int(self.interval[:-1])
        unit = self.interval[-1]
        return scale, unit

    def fetch_df(self, symbol: str) -> pd.DataFrame:
        """"""

        df = pd.DataFrame(
            self.engine.fetch_ohlcv(symbol, timeframe=self.interval, limit=500)
        )
        df.columns = [
            "datetime", "open", "high", "low", "close", "volume"
        ]
        df["datetime"] = pd.to_datetime(
            df["datetime"].apply(self.engine.iso8601), utc=True
        )
        df.set_index("datetime", inplace=True)
        return df

    def get_datetime(self) -> Tuple:
        """"""

        scale, unit = self.split_interval()
        num = scale * self.window

        if unit == "m":
            cur_dt = pd.to_datetime(
                datetime.utcnow().strftime("%Y-%m-%d %H:%M"), utc=True
            )
            pre_dt = cur_dt - timedelta(hours=num)
        elif unit == "h":
            cur_dt = pd.to_datetime(
                datetime.utcnow().strftime("%Y-%m-%d %H"), utc=True
            )
            pre_dt = cur_dt - timedelta(hours=num)
        elif unit == "d":
            cur_dt = pd.to_datetime(
                datetime.utcnow().strftime("%Y-%m-%d"), utc=True
            )
            pre_dt = cur_dt - timedelta(days=num)
        elif unit == "W":
            pass
        elif unit == "M":
            pass
        else:
            pass

        return pre_dt, cur_dt

    def calc_return(self, series: pd.Series) -> Tuple:
        """"""

        pre_dt, cur_dt = self.get_datetime()
        pre_price, cur_price = series[pre_dt], series[cur_dt]
        calc_series = series[series.index >= pre_dt] / pre_price

        rtn = (cur_price - pre_price) / pre_price

        return rtn, calc_series

    def show_result(
            self, calc_date: datetime, rtn_dict: Dict
    ) -> None:
        """"""

        rtn_list = sorted(
            rtn_dict.items(), key=lambda x: x[1], reverse=True
        )

        output = "="*50 + f"\nDatetime (UTC): {calc_date}" \
                 f"\nParameters | Interval: {self.interval}, " \
                 f"Window: {self.window}\n" + "="*50 + "\n"
        count = 1
        for info in rtn_list:
            symbol, rtn = info
            output += f"\t{count} \t| \t{symbol}: \t{rtn * 100}%\n"
            count += 1
        output += "="*50

        print(output)

    def show_plot(
            self, calc_date: datetime,
            rtn_dict: Dict, trace_dict: Dict
    ) -> None:
        """"""

        subtitle1 = f"Date: {calc_date} | Crypto Return | Interval: {self.interval} | Window: {self.window}"
        subtitle2 = f"Date: {calc_date} | Crypto Momentum | Interval: {self.interval} | Window: {self.window}"
        fig = make_subplots(
            rows=2, cols=1, subplot_titles=(subtitle1, subtitle2)
        )

        rtn_series = pd.Series(rtn_dict).sort_values(ascending=False)
        rtn_trace = go.Bar(
            x=rtn_series.index, y=rtn_series.values,
            name="Crypto"
        )

        trend_traces = []
        for symbol, series in trace_dict.items():
            trend_traces.append(
                go.Scatter(
                    x=series.index, y=series.values,
                    mode="lines", name=symbol
                )
            )

        fig.add_traces([rtn_trace], rows=1, cols=1)
        fig.add_traces(trend_traces, rows=2, cols=1)

        plotly.offline.plot(fig, filename="crypto_mom.html")

    def mom_main(self):
        """"""

        rtn_dict = {}
        trace_dict = {}
        dts = []
        for symbol in self.symbols:

            df = self.fetch_df(symbol)

            dts.append(df.index.to_numpy()[-1])

            rtn, prices = self.calc_return(df["close"])

            rtn_dict[symbol] = round(rtn, 5)
            trace_dict[symbol] = prices

        if not len(list(set(dts))) == 1:
            print(f"Last Dates: {set(dts)}")

        self.show_result(dts[0], rtn_dict)

        self.show_plot(dts[0], rtn_dict, trace_dict)

        return rtn_dict


if __name__ == "__main__":
    """"""

    # crypto_ex = "binance"
    crypto_ex = "huobipro"
    # crypto_ex = "okex"
    proxies = True
    tickers = [
        "BTC/USDT", "ETH/USDT", "DOT/USDT",
        "FLOW/USDT", "SOL/USDT", "UNI/USDT"
    ]
    calc_interval = "1h"
    calc_window = 20 * 24

    mom_engine = MomEngine(
        crypto_ex, proxies, tickers, calc_interval, calc_window
    )

    symbol_dict = mom_engine.mom_main()