from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)
from vnpy.app.cta_strategy.base import (
    EngineType,
    StopOrder,
    StopOrderStatus,
)
from datetime import datetime
from decimal import Decimal
from vnpy.trader.constant import (Direction, Offset, Exchange, Interval, Status, OrderType)
import talib


class HPTP_big_volume(CtaTemplate):
    """"""
    author = "hwk"
    interval = Interval.HOUR
    MaxPercent = 8
    Length = 210
    StopATR = 10
    StopPercent = 22  # 主要是为了避免在5倍USDT杠杆下被强平的问题
    ATRRisk = 30000
    MaxCapital = 10000000

    # 数字(int,float,decimal,bool,string,tuple,range)在Python中属于不可变对象，因此每个策略的lastPrice互不影响
    # 可变类型:list,dict,set: 可以不用在类上面初定义，但必须在类的__init__中进行初始化，否则在同一策略创建多个策略对象时，可变类型变量会混
    lots = 0.0
    PlanCapital = 0.0
    VolMa = 0.0
    HCLine = 0.0
    LCLine = 0.0
    HCLine_Pre = 0.0
    LCLine_Pre = 0.0
    HighestAfterEntry = 0.0
    LowestAfterEntry = 0.0
    ATR = 0.0
    stop_atr = 0.0
    track_stop = 0.0
    fix_stop = 0.0
    StopLine = 0.0
    buy_order_price = 0.0     # 价格也要初始化，用于策略重启时恢复变量，以免多个类的价格混乱了
    short_order_price = 0.0
    sell_order_price = 0.0
    cover_order_price = 0.0
    BarTime = 0.0
    BuySignal = False
    ShortSignal = False
    HCond = False
    LCond = False
    StayCond = False

    parameters = ["MaxPercent", "Length", "StopATR", "StopPercent", "MaxCapital"]

    variables = [
        "BarTime", "PlanCapital", "ATRRisk", "HCLine", "LCLine", "HCLine_Pre", "LCLine_Pre",
        "HighestAfterEntry", "LowestAfterEntry", "StopLine", "lots", "VolMa", "ATR", "BuySignal",
        "ShortSignal", "StayCond", "stop_atr", "track_stop", "fix_stop", "buy_order_price",
        "short_order_price", "sell_order_price", "cover_order_price"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.engine_type = self.get_engine_type()
        if self.engine_type == EngineType.LIVE:
            self.pricetick = self.get_pricetick()
            self.min_volume = str(self.get_min_volume())
        else:
            self.pricetick = 1e-06
            self.min_volume = str(1e-04)

        # 所有的可变数据结构，在这里一定要重新初始化
        # 区分buy 和 sell 的 orderid不然在平仓环节的撤单，可能把开仓的单子给撤了
        self.buy_vt_orderids = []
        self.short_vt_orderids = []
        self.sell_vt_orderids = []
        self.cover_vt_orderids = []

        if self.interval == Interval.HOUR:
            if self.engine_type == EngineType.LIVE:
                # 实盘暂时改为了用60根分钟Bar推动合成
                self.bg = BarGenerator(
                    on_bar=self.on_bar,
                    window=60,
                    on_window_bar=self.on_hour_bar,
                    interval=Interval.MINUTE)

            elif self.engine_type == EngineType.BACKTESTING:
                # 目前小时Bar更新逻辑有些问题，实盘暂时改为了用60根分钟Bar推动合成
                self.bg = BarGenerator(
                    on_bar=self.on_bar,
                    window=1,
                    on_window_bar=self.on_hour_bar,
                    interval=self.interval)

        elif self.interval == Interval.MINUTE:
            self.bg = BarGenerator(
                on_bar=self.on_bar,
                window=60,
                on_window_bar=self.on_hour_bar,
                interval=self.interval)

        self.am = ArrayManager(size=int(self.Length + 10))

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")
        if self.engine_type == EngineType.LIVE:
            self.load_bar(days=self.Length//24 + 1, interval=Interval.MINUTE)
        else:
            self.load_bar(days=self.Length//24 + 1, interval=self.interval)

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.write_log("策略启动")

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")
        self.sync_data()  # 自己新增

    def cancel_orders(self, vt_orderids: list):
        """"""
        for vt_orderid in vt_orderids:
            self.cancel_order(vt_orderid)

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        # 在on_tick里面使用target_pos可以解决部分成交再发单的情况（前提是self.pos已经准确更新）
        # 如果当前tick撤单，再次发单的时候要等到下一个tick，如果是同一根tick想要再次发单，没法保证此时单子已经撤完了（on order在撤单时没有被回调）
        # 来了tick应该先合成bar，因为在on_window_bar里面可能会更新信号和target_pos
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.bg.update_bar(bar)
        # self.write_log("分钟Bar时间戳{}，收盘价{}，最高价{}，最低价{}".
        #                format(bar.datetime, bar.close_price, bar.high_price, bar.low_price))

    def on_hour_bar(self, bar: BarData):
        """"""
        # self.cancel_all()
        # 目前该策略发单的逻辑是仅会在该跟Bar发出建仓的信号，因此如果建仓的信号被撤单后，在下一根Bar也不会再重新发单了；
        # 不过对于平仓信号，当前Bar无法平仓的信号，下一根Bar也需要再次重新发单平仓
        self.BarTime = str(bar.datetime)

        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        self.ATR = am.atr(self.Length)

        # 用 close 价格发单比 high/low 价格发单效果差不多，注意这里用 high/low 价格会过滤的更严格
        self.HCLine = max(am.close_array[-self.Length:])
        self.LCLine = min(am.close_array[-self.Length:])

        self.StayCond = int((self.HCLine - self.LCLine) / bar.close_price <= self.MaxPercent / 100)

        # 把其他的突破价格写在外面，突破的价格直接用stop order触发即可
        # self.HCond = bar.close_price >= self.HCLine and am.close_array[-2] < self.HCLine_Pre
        # self.LCond = bar.close_price <= self.LCLine and am.close_array[-2] > self.LCLine_Pre

        self.HCond = 1
        self.LCond = 1

        self.BuySignal = int(self.HCond and self.StayCond)
        self.ShortSignal = int(self.LCond and self.StayCond)

        if self.pos == 0.0:
            if self.BuySignal or self.ShortSignal:
                self.lots = self.ATRRisk / self.ATR
                self.PlanCapital = self.lots * bar.close_price

                if self.PlanCapital > self.MaxCapital:
                    self.lots = self.MaxCapital / bar.close_price

                # 计算24小时内的成交量，注意当周期变的时候，这里的参数值也要改变
                self.VolMa = talib.EMA(am.volume_array[-24:], 24)[-1]

                # 流动性过滤对于提高策略绩效也起到了很好的作用，流动性好的品种趋势性似乎也好
                # if self.lots >= self.VolMa / 100:
                #     self.lots = self.VolMa / 100

                self.lots = float(Decimal(str(self.lots)).quantize(Decimal(self.min_volume)))

                if self.lots > 0.0:
                    if not self.buy_vt_orderids:
                        if self.BuySignal:
                            self.buy_order_price = self.HCLine
                            buy_vt_orderids = self.buy(self.buy_order_price, self.lots, stop=True)
                            self.buy_vt_orderids.extend(buy_vt_orderids)
                            self.BuySignal = False  # 这里一定要再变为False，否则其他stop_order在撤单时，也可能会触发该方向的信号
                            self.HighestAfterEntry = self.buy_order_price
                            self.write_log("开多{}手,时间{},订单{}".format(self.lots, bar.datetime, self.buy_vt_orderids))
                    # 这里与else直接撤单不同，可能会让某个单子一直挂单很近，反向的单子可能都已经成交了，这个单子可能还会在挂着
                    # 但目前测试下来这个写法效果更好一些，并且如果进场价一旦有更新的话，仍然是会撤单的
                    # 这样写可能的好处是，在同一根 Window Bar 里面，如果反向单子已经成交了，然后价格又在同一根Bar反向变动而触发了此单子
                    # 这时就可以实现在同一根Bar里面完成两个方向单子的进出场了
                    elif self.buy_order_price != self.HCLine:
                        self.cancel_orders(self.buy_vt_orderids)
                        self.write_log("撤单开多时间{},订单{}".format(bar.datetime, self.buy_vt_orderids))

                    if not self.short_vt_orderids:
                        if self.ShortSignal:
                            self.short_order_price = self.LCLine
                            short_vt_orderids = self.short(self.short_order_price, self.lots, stop=True)
                            self.short_vt_orderids.extend(short_vt_orderids)
                            self.ShortSignal = False
                            self.LowestAfterEntry = self.short_order_price
                            self.write_log("开空{}手,时间{},订单{}".format(self.lots, bar.datetime, self.short_vt_orderids))

                    elif self.short_order_price != self.LCLine:
                        self.cancel_orders(self.short_vt_orderids)
                        self.write_log("撤单开多时间{},订单{}".format(bar.datetime, self.short_vt_orderids))

        else:
            if self.pos > 0.0:
                self.HighestAfterEntry = max(self.HighestAfterEntry, bar.high_price)
                self.stop_atr = self.HighestAfterEntry - self.StopATR * self.ATR
                # self.fix_stop = self.buy_order_price * (1 - self.StopPercent / 100)   # 固定止损
                self.fix_stop = self.HighestAfterEntry * (1 - self.StopPercent / 100)   # 跟踪止损

                self.StopLine = max(self.stop_atr, self.fix_stop)

                if not self.sell_vt_orderids:
                    self.sell_order_price = self.StopLine
                    sell_vt_orderids = self.sell(self.sell_order_price, self.pos, stop=True)
                    self.sell_vt_orderids.extend(sell_vt_orderids)
                    self.write_log("平多{}手,时间{},订单{}".format(self.pos, bar.datetime, self.sell_vt_orderids))
                elif self.sell_order_price != self.StopLine:
                    self.cancel_orders(self.sell_vt_orderids)
                    self.write_log("撤单平多时间{},订单{}".format(bar.datetime, self.sell_vt_orderids))

            elif self.pos < 0.0:
                self.LowestAfterEntry = min(self.LowestAfterEntry, bar.low_price)
                self.stop_atr = self.LowestAfterEntry + self.StopATR * self.ATR
                # self.fix_stop = self.short_order_price * (1 + self.StopPercent / 100)  # 固定止损
                self.fix_stop = self.LowestAfterEntry * (1 + self.StopPercent / 100)     # 跟踪止损
                # 当策略中途重启时，如果此时已经持有空仓，这时 self.short_order_price = 0，
                # 会导致重启后就直接平掉空头仓位了， 因为空头平仓是用的min价格，可能最小为0，
                # 此时重启策略前，应该先将策略的进场价位，即self.short_order_price 手动同步
                self.StopLine = min(self.stop_atr, self.fix_stop)

                if not self.cover_vt_orderids:
                    self.cover_order_price = self.StopLine
                    cover_vt_orderids = self.cover(self.cover_order_price, abs(self.pos), stop=True)
                    self.cover_vt_orderids.extend(cover_vt_orderids)
                    self.write_log("平空{}手,时间{},订单{}".format(abs(self.pos), bar.datetime, self.cover_vt_orderids))
                elif self.cover_order_price != self.StopLine:
                    self.cancel_orders(self.cover_vt_orderids)
                    self.write_log("撤单平空时间{},订单{}".format(bar.datetime, self.cover_vt_orderids))

        self.sync_data()   # 自己新增，用于实现无人值守版本以在json文件记录每个Window Bar中更新的变量
        self.put_event()

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        cancel order 不会调用on_order (on order只在有new order data时被调用)

        限价单会进入到交易所，停止单只有触发的时候才会发送，本地停止单也是先转换到了服务器限价单的，限价单会调用on_order函数
        考虑部分成交，然后再撤单之后重发时，交易手数会不会出问题

        成交后，先推送委托状态更新OrderData，再推送成交信息TradeData
        # 如果要用限价单重新发单时，需要更新买入价格
        """

        self.write_log("本地时间{},order时间{},状态{},成交{}手".format(datetime.now(), order.datetime, order.status, order.traded))

        # 只有收到order 交易所撤单回报的时候，才能认为该交易已撤单，
        # cancel_order 不能保证一定能成功撤单，可能等下就成交了，或者撤单被交易所拒绝了

        # 虽然非CTP行情，比如币安的fix协议的话，order和trade信息是同时发送过来，但在gateway里面也同样的是先调用on_order再调用on_trade
        # 但存在一直可能就是，已经成交了，但交易所服务器一直没有推给trade的信息过来的话，self.pos就不会先更新
        # （先收到成交回报，再更新self.pos，最后才是调用on_trade）

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        在 paper account下，收到on_trade时，self.pos 可能更新了，也可能没更新
        但数字货币和CTP的接口中，都是先回报调用on_order，再调用on_trade
        """
        # if abs(self.pos) <= self.min_volume:
        #     self.pos = 0.0

        # 每次收到成交回报，都立刻再把self.pos的小数位精确一次
        self.pos = float(Decimal(str(self.pos)).quantize(Decimal(self.min_volume)))

        msg = f"成交时间{trade.datetime},当前仓位{self.pos},报单号{trade.orderid}," \
              f"方向{trade.direction},开平{trade.offset},成交数量{trade.volume}"

        # self.send_email(msg)
        self.write_log(msg)

        self.sync_data()  # 在trade event里面有成交时会自动同步数据，这里可能不需要再重复添加了（影响不大，反正已经成交了）
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        # cancel stop order 会回调本函数，不过cancel order 不会调用on_order (on order只在有new order data时被调用)
        # 每个tick会查看本地stop单是否触发，如果触发就以tick.limit_up或者对价5档吃单

        # 只处理撤销或者触发的停止单委托
        if stop_order.status == StopOrderStatus.WAITING:
            return

        # 移除已经“已撤销”或者“已触发”的停止单委托号
        if stop_order.stop_orderid in self.buy_vt_orderids:
            self.buy_vt_orderids.remove(stop_order.stop_orderid)

            # 若是撤单，且目前无仓位，则立即重发; 如果状态是TRIGGERED,此时单子是刚刚发出来就立刻调用了stop order，
            # 成没成交还不知道呢，单线程下self.pos也肯定还没变呢
            if self.BuySignal and stop_order.status == StopOrderStatus.CANCELLED \
                    and not self.pos and not self.buy_vt_orderids:
                self.buy_order_price = self.HCLine
                buy_vt_orderids = self.buy(self.buy_order_price, self.lots, stop=True)
                self.buy_vt_orderids.extend(buy_vt_orderids)
                self.BuySignal = False
                self.HighestAfterEntry = self.buy_order_price
                self.write_log("重发开多{}手,时间{},订单{}".format(self.lots, datetime.now(), self.buy_vt_orderids))

        elif stop_order.stop_orderid in self.short_vt_orderids:
            self.short_vt_orderids.remove(stop_order.stop_orderid)

            if self.ShortSignal and stop_order.status == StopOrderStatus.CANCELLED \
                    and not self.pos and not self.short_vt_orderids:
                self.short_order_price = self.LCLine
                short_vt_orderids = self.short(self.short_order_price, self.lots, stop=True)
                self.short_vt_orderids.extend(short_vt_orderids)
                self.ShortSignal = False
                self.LowestAfterEntry = self.short_order_price
                self.write_log("重发开空{}手,时间{},订单{}".format(self.lots, datetime.now(), self.short_vt_orderids))

        elif stop_order.stop_orderid in self.sell_vt_orderids:
            self.sell_vt_orderids.remove(stop_order.stop_orderid)

            if stop_order.status == StopOrderStatus.CANCELLED and self.pos > 0 and not self.sell_vt_orderids:
                self.sell_order_price = self.StopLine
                sell_vt_orderids = self.sell(self.sell_order_price, self.pos, stop=True)
                self.sell_vt_orderids.extend(sell_vt_orderids)
                self.write_log("重发平多{}手,时间{},订单{}".format(self.pos, datetime.now(), self.sell_vt_orderids))

        elif stop_order.stop_orderid in self.cover_vt_orderids:
            self.cover_vt_orderids.remove(stop_order.stop_orderid)

            if stop_order.status == StopOrderStatus.CANCELLED and self.pos < 0 and not self.cover_vt_orderids:
                self.cover_order_price = self.StopLine
                cover_vt_orderids = self.cover(self.cover_order_price, abs(self.pos), stop=True)
                self.cover_vt_orderids.extend(cover_vt_orderids)
                self.write_log("重发平空{}手,时间{},订单{}".format(abs(self.pos), datetime.now(), self.cover_vt_orderids))
