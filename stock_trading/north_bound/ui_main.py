import sys
from datetime import datetime, timedelta
from pandas import DataFrame
from PyQt5.QtWidgets import QApplication, QMainWindow
from nb import MainWindowUI
from signal_northbound import NorthBound


class MainWindow(QMainWindow):
    """"""

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = MainWindowUI()
        self.ui.setupUi(self)

    @staticmethod
    def quantize_north_bound(
            interval: float, upper: float, lower: float, df: DataFrame
    ) -> tuple:
        """"""

        current_date = datetime.now()
        start_date = current_date - timedelta(days=365 * interval)
        cal_data = df[
            (df.index >= start_date) & (df.index <= current_date)
        ]["north_money"]

        br, sr = cal_data.quantile(upper), cal_data.quantile(lower)

        return br, sr

    @staticmethod
    def output_result(
            date: datetime, north_bound: float,
            buy_region: float, sell_region: float
    ) -> str:
        """"""

        hline = "=" * 80 + "\n"
        date_line = f"Date: {date}\n"
        value_line = f"North Money Value: {north_bound} Mil\n"
        threshold_line = f"Buy Region: {buy_region} Mil | Sell Region: {sell_region} Mil\n"

        output = hline + date_line + value_line + threshold_line + hline

        return output

    def main_result(
            self, interval: float, upper: float, lower: float
    ):
        """"""

        north_bound = NorthBound()

        hs_df, _ = north_bound.main_one_record()

        b_r, s_r = self.quantize_north_bound(
            interval=interval, upper=upper, lower=lower, df=hs_df
        )

        cal_date = hs_df.index[-1]
        north_money = hs_df.loc[cal_date, "north_money"]

        output = self.output_result(cal_date, north_money, b_r, s_r)
        return output

    def calc_bound(self):
        """"""

        interval = self.ui.lineEdit.text()
        upper = self.ui.lineEdit_2.text()
        lower = self.ui.lineEdit_3.text()

        if not upper:
            upper = 3 / 4
        else:
            upper = float(upper)
        if not lower:
            lower = 1 / 4
        else:
            lower = float(lower)

        interval = float(interval)

        output = self.main_result(
            interval=interval, upper=upper, lower=lower
        )
        self.ui.plainTextEdit.setPlainText(output)

    def clear_result(self):
        """
        clear the output in Text Editor
        """

        self.ui.plainTextEdit.clear()


if __name__ == "__main__":

    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec_())

