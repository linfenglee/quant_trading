from datetime import datetime, timedelta
import pandas as pd
from signal_northbound import NorthBound


def quantize_north_bound(
        interval: float, upper: float, lower: float, df: pd.DataFrame
) -> tuple:
    """"""

    current_date = datetime.now()
    start_date = current_date - timedelta(days=365 * interval)
    cal_data = df[
        (df.index >= start_date) & (df.index <= current_date)
    ]["north_money"]

    br, sr = cal_data.quantile(upper), cal_data.quantile(lower)

    return br, sr


def show_result(
        date: datetime, north_bound: float,
        buy_region: float, sell_region: float
) -> None:
    """"""

    print("="*80)

    output = f"Date: {date}\nNorth Money Value: {north_bound} Mil\nBuy Region: {buy_region} Mil | Sell Region: {sell_region} Mil"

    print(output)

    print("="*80)


def main(interval: float, upper: float, lower: float) -> None:
    """"""

    # initialize North Bound Download Engine
    north_bound = NorthBound()

    hs_df, _ = north_bound.main_one_record()

    b_r, s_r = quantize_north_bound(
        interval=interval, upper=upper, lower=lower, df=hs_df
    )

    cal_date = hs_df.index[-1]
    north_money = hs_df.loc[cal_date, "north_money"]

    show_result(cal_date, north_money, b_r, s_r)


if __name__ == "__main__":
    """"""

    main(interval=1, upper=3/4, lower=1/4)