import json
import time
from typing import List
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait


class EastMoneyEngine(object):
    """"""

    def __init__(self):
        """"""

        self.paths = self.init_paths()
        self.driver = self.init_webdriver()

    def __del__(self):
        """"""
        self.driver.close()

    @staticmethod
    def init_paths():
        """"""
        with open("./paths.json") as f:
            paths = json.load(f)
        return paths

    def init_webdriver(self):
        """"""

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(
            executable_path=self.paths["webdriver"], options=chrome_options
        )

        return driver

    def get_column_name(self):
        """"""
        thead = self.driver.find_elements_by_tag_name("thead")[-1]
        ths = thead.find_elements_by_tag_name("th")
        cols = []
        for th in ths:
            cols.append(th.text.replace("\n", ""))
        return cols

    def get_pages(self) -> int:
        """"""
        element = self.driver.find_element_by_class_name("pagerbox")
        max_page = element.find_elements_by_tag_name("a")[-2]
        pages = int(max_page.text)
        return pages

    def get_next_page(self):
        """"""
        element = self.driver.find_element_by_class_name("pagerbox")
        next_page_btn = element.find_elements_by_tag_name("a")[-1]
        if next_page_btn.text == "下一页":
            next_page_btn.click()
            return True
        else:
            return False

    def get_dataview(self) -> List:
        """"""

        element = self.driver.find_element_by_class_name("dataview")
        trs = element.find_elements_by_tag_name("tr")

        content = []
        for tr in trs:
            tds = tr.find_elements_by_tag_name("td")
            if len(tds) == 0:
                continue
            row_info = []
            for td in tds:
                row_info.append(td.text)
            content.append(row_info)

        return content

    def lhb_yyb_analysis(self):
        """"""

        url = self.paths["lhb_yyb"]
        self.driver.get(url=url)

        columns = self.get_column_name()

        # pages = self.get_pages()
        content = []
        while True:

            page_content = self.get_dataview()
            content.extend(page_content)

            res = self.get_next_page()
            if not res:
                break

            _ = WebDriverWait(self.driver, 5)

        df = pd.DataFrame(data=content, columns=columns)

        df.drop_duplicates(inplace=True, ignore_index=True)
        df.set_index("序号", inplace=True)

        return df

    @staticmethod
    def get_lhb(table) -> pd.DataFrame:
        """"""

        thead = table.find_element_by_tag_name("thead")
        ths = thead.find_elements_by_tag_name("th")
        columns = []
        for th in ths:
            columns.append(th.text)
        trs = table.find_elements_by_tag_name("tr")
        content = []
        for tr in trs:
            tds = tr.find_elements_by_tag_name("td")
            row_info = []
            for td in tds:
                row_info.append(td.text)
            content.append(row_info)
        lhb_df = pd.DataFrame(data=content, columns=columns)

        return lhb_df

    def get_stock_lhb(self):
        """"""

        tables = self.driver.find_elements_by_tag_name("table")
        if len(tables) == 3:
            buy_table, sell_table = tables[1], tables[2]
        else:
            return pd.DataFrame()

        buy_df = self.get_lhb(buy_table)
        buy_df["方向"] = "买入"
        sell_df = self.get_lhb(sell_table)
        sell_df["方向"] = "卖出"
        df = pd.concat([buy_df, sell_df], ignore_index=True)

        return df

    def lhb_stocks_analysis(self):
        """"""

        yyb_df = self.lhb_yyb_analysis()
        base_url = self.paths["lhb_stock"]
        data = pd.DataFrame()
        for code in yyb_df["代码"]:
            lhb_url = f"{base_url}{code}.html"
            self.driver.get(lhb_url)
            lhb_df = self.get_stock_lhb()
            if lhb_df.empty:
                continue
            lhb_df["代码"] = code
            data = pd.concat([data, lhb_df], ignore_index=True)

        data.to_csv("lhb_stocks.csv")


if __name__ == "__main__":
    """"""

    engine = EastMoneyEngine()

    # lhb_yyb_df = engine.lhb_yyb_analysis()

    engine.lhb_stocks_analysis()