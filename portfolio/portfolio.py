import builtins
from collections import defaultdict
from datetime import datetime, timedelta

from tabulate import tabulate
import matplotlib.pyplot as plt

from portfolio.base import (
    TimeRange, Value, ValueList, date_to_key, key_to_date)
from portfolio.config import CBR_RATE, CBR_BASE_RATE
from portfolio.loaders import QuotesLoader
from portfolio.managers import (
    QuotesManager, OrdersManager, MoneyManagerCached, SecuritiesManager,
    Order, Money, DividendManager, CommissionManager)


class Portfolio:
    RUB = 'RUB'
    USD = 'USD'
    EUR = 'EUR'
    CURRENCIES = (RUB, USD, EUR, )
    MB = 'MB'
    SPB = 'SPB'
    MARKETS = (MB, SPB, )

    FXIT = 'IE00BD3QJ757'
    FXUS = 'IE00BD3QHZ91'
    FXRL = 'IE00BQ1Y6480'
    FXRB = 'IE00B7L7CP77'
    FUNDS = (FXIT, FXUS, FXRL, FXRB, )

    def __init__(self, portfolio_id, broker_id=None):
        self.portfolio_id = portfolio_id
        self.broker_id = broker_id

    def chart(self, start_date, end_date, currency=RUB):
        time_range = TimeRange(start_date, end_date)

        data = self.get_value_history(time_range, currency=currency)
        cbr_data = self.get_cbr_history(time_range, currency=currency)
        cash_data = self.get_cash_history(time_range, currency=currency)
        dividend_data = self.get_dividend_history(time_range,
                                                  currency=currency)
        commission_data = self.get_commission_history(time_range,
                                                      currency=currency)

        funds_data = [self.get_fund_history(cash_data, fund, currency=currency)
                      for fund in self.FUNDS]

        self.add_charts(dividend_data + data, cbr_data, cash_data, data,
                        step=50000)
        self.add_charts(dividend_data + data, *funds_data, step=50000)
        self.add_charts(data - cash_data, cbr_data - cash_data,
                        dividend_data, commission_data)
        self.add_charts(100 * (data - cash_data) / cash_data,
                        100 * (data + dividend_data - cash_data) / cash_data,
                        100 * (cbr_data - cash_data) / cash_data, step=10)

        self.show_charts()

    def get_value_history(self, time_range, currency=RUB):
        changes = {
            'JE00B5BCW814': 'RU000A1025V3',
            'je00b5bcw814': 'ru000a1025v3',
        }
        usd = QuotesManager.get_quotes(self.USD, time_range)
        eur = QuotesManager.get_quotes(self.EUR, time_range)

        value = ValueList('value')
        prev_price = {}
        portfolio = defaultdict(int)
        operations = defaultdict(list)
        orders_range = TimeRange(None, time_range.end_time)
        stock_orders = OrdersManager.get_data(
            self.portfolio_id, orders_range, broker_id=self.broker_id)
        money_orders = MoneyManagerCached.get_data(
            self.portfolio_id, orders_range, broker_id=self.broker_id)
        all_orders = money_orders + stock_orders
        all_orders.sort(key=lambda x: x[0])

        cur_range = TimeRange(key_to_date(all_orders[0].date),
                              time_range.end_time)
        dates = self.get_dates(cur_range)

        for order in all_orders:
            operations[order.date].append(order)
            if isinstance(order, Money):
                continue
            if isinstance(order, Order):
                quantity = order.quantity
                portfolio[order.isin] += quantity
                if portfolio[order.isin] < 0:
                    raise ValueError()

        portfolio = defaultdict(int)
        for date in dates:
            day_orders = operations[date]
            self._update_portfolio_dict(portfolio, day_orders)

            if date < time_range.start:
                continue

            if date in usd:
                prev_price[self.USD] = usd[date]
            if date in eur:
                prev_price[self.EUR] = eur[date]

            portfolio_sum = 0
            for key, quantity in portfolio.items():
                isin, cur = key
                if isin == self.RUB:
                    portfolio_sum += quantity
                elif isin == self.USD:
                    c = usd.get(date, prev_price[self.USD])
                    portfolio_sum += c * quantity
                elif isin == self.EUR:
                    c = eur.get(date, prev_price[self.EUR])
                    portfolio_sum += c * quantity
                else:
                    if isin in changes:
                        isin = changes[isin]
                    candles = QuotesManager.get_quotes(isin, time_range)
                    if date in candles:
                        c1 = candles[date]
                        prev_price[isin] = c1
                    else:
                        c1 = prev_price[isin]

                    security = SecuritiesManager.get_data(isin=isin)
                    cur = security['currency']

                    if cur == self.RUB:
                        c2 = 1
                    elif cur == self.USD:
                        c2 = usd.get(date, prev_price[self.USD])
                    elif cur == self.EUR:
                        c2 = eur.get(date, prev_price[self.EUR])
                    else:
                        raise ValueError(cur)

                    portfolio_sum += c1 * c2 * quantity

            if currency == self.USD:
                c3 = usd.get(date, prev_price[self.USD])
            elif currency == self.EUR:
                c3 = eur.get(date, prev_price[self.EUR])
            else:
                c3 = 1

            day_value = Value()
            day_value.key = date
            day_value.value = portfolio_sum / c3
            value.append(day_value)
        return value

    def _update_portfolio_dict(self, portfolio, orders):
        for order in orders:
            cur = order.cur
            sum = order.sum
            if isinstance(order, Order):
                isin = order.isin
                quantity = order.quantity
                if quantity < 0 and not portfolio[(isin, cur)]:
                    q = abs(quantity)
                    for tcur in self.CURRENCIES:
                        if not portfolio[(isin, tcur)]:
                            continue
                        sub = min(portfolio[(isin, tcur)], q)
                        portfolio[(isin, tcur)] -= sub
                        q -= sub
                    if q:
                        raise ValueError()
                else:
                    portfolio[(isin, cur)] += quantity

                if quantity > 0 and not portfolio[(cur, cur)]:
                    s = sum
                    for tcur in self.CURRENCIES:
                        if not portfolio[(cur, tcur)]:
                            continue
                        sub = min(portfolio[(cur, tcur)], s)
                        portfolio[(cur, tcur)] -= sub
                        s -= sub
                    if s > 0:
                        raise ValueError()
                else:
                    portfolio[(cur, cur)] -= quantity / abs(quantity) * sum
            if isinstance(order, Money):
                portfolio[(cur, cur)] += sum

    def get_value(self):
        changes = {
            'JE00B5BCW814': 'RU000A1025V3',
            'je00b5bcw814': 'ru000a1025v3',
        }

        usd_based = (
            self.FXIT,  # FXIT
            self.FXUS,  # FXUS
        )

        usd = QuotesLoader.current(self.USD)
        eur = QuotesLoader.current(self.EUR)

        by_cur = defaultdict(int)

        orders_range = TimeRange(None, datetime.now())
        stock_orders = OrdersManager.get_data(
            self.portfolio_id, orders_range, broker_id=self.broker_id)
        money_orders = MoneyManagerCached.get_data(
            self.portfolio_id, orders_range, broker_id=self.broker_id)
        all_orders = money_orders + stock_orders
        all_orders.sort(key=lambda x: x[0])

        portfolio = defaultdict(int)
        self._update_portfolio_dict(portfolio, all_orders)

        portfolio_sum = 0
        active_sum = 0
        for key, quantity in portfolio.items():
            if not quantity:
                continue
            isin, cur = key

            if isin == self.RUB:
                position = quantity
            elif isin == self.USD:
                c = usd
                position = c * quantity
            elif isin == self.EUR:
                c = eur
                position = c * quantity
            else:
                if isin in changes:
                    isin = changes[isin]
                c1 = QuotesLoader.current(isin)

                security = SecuritiesManager.get_data(isin=isin)
                cur = security['currency']

                if cur == self.RUB:
                    c2 = 1
                elif cur == self.USD:
                    c2 = usd
                elif cur == self.EUR:
                    c2 = eur
                else:
                    raise ValueError(cur)

                position = c1 * c2 * quantity
            portfolio_sum += position
            if key[0] != key[1]:
                active_sum += position

            if isin in usd_based:
                cur = self.USD
            by_cur[cur] += position

        for key in by_cur:
            by_cur[key] = by_cur[key] / portfolio_sum * 100

        cash = {}
        for key in portfolio:
            if key[0] == key[1]:
                cash[key[0]] = portfolio[key]

        return portfolio_sum, active_sum, by_cur, cash

    def get_state(self):
        changes = {
            'JE00B5BCW814': 'RU000A1025V3',
            'je00b5bcw814': 'ru000a1025v3',
        }

        usd = QuotesLoader.current(self.USD)
        eur = QuotesLoader.current(self.EUR)

        orders_range = TimeRange(None, datetime.now())
        stock_orders = OrdersManager.get_data(
            self.portfolio_id, orders_range, broker_id=self.broker_id)
        money_orders = MoneyManagerCached.get_data(
            self.portfolio_id, orders_range, broker_id=self.broker_id)
        all_orders = money_orders + stock_orders
        all_orders.sort(key=lambda x: x[0])

        portfolio = defaultdict(int)
        self._update_portfolio_dict(portfolio, all_orders)

        state_asset = []
        asset_sum = 0
        state_cur = []
        for key, quantity in portfolio.items():
            if not quantity:
                continue
            isin, cur = key
            ticker = name = isin
            sec_cur = isin
            position_orig = quantity

            if isin == self.RUB:
                position = position_orig = quantity
            elif isin == self.USD:
                c = usd
                position = c * quantity
            elif isin == self.EUR:
                c = eur
                position = c * quantity
            else:
                if isin in changes:
                    isin = changes[isin]
                c1 = QuotesLoader.current(isin)

                security = SecuritiesManager.get_data(isin=isin)
                sec_cur = security['currency']
                ticker = security['ticker']
                name = security['name']

                if sec_cur == self.RUB:
                    c2 = 1
                elif sec_cur == self.USD:
                    c2 = usd
                elif sec_cur == self.EUR:
                    c2 = eur
                else:
                    raise ValueError(sec_cur)

                position = c1 * c2 * quantity
                position_orig = c1 * quantity

            position = builtins.round(position, 2)
            position_orig = builtins.round(position_orig, 2)
            if ticker == sec_cur:
                state_cur.append([ticker, name, quantity, sec_cur,
                                  position_orig, position])
            else:
                state_asset.append([ticker, name, quantity, sec_cur,
                                    position_orig, position])
                asset_sum += position
        state_asset.append(['All', '', '', '', '', asset_sum])
        return state_asset, state_cur

    def show_state(self):
        state_asset, state_cur = self.get_state()
        state = tabulate(state_cur, headers=["Ticker", "Name", "Quantity",
                                             "Cur", "Sum", "Sum (rub)"])
        print(state)
        state = tabulate(state_asset, headers=["Ticker", "Name", "Quantity",
                                               "Cur", "Sum", "Sum (rub)"])
        print(state)

    def get_cbr_history(self, time_range, currency=RUB):
        money_range = TimeRange(None, time_range.end_time)
        money_orders = MoneyManagerCached.get_data(
            self.portfolio_id, money_range, broker_id=self.broker_id)
        cur_range = TimeRange(key_to_date(money_orders[0].date),
                              time_range.end_time)
        usd = QuotesManager.get_quotes(self.USD, cur_range)
        eur = QuotesManager.get_quotes(self.EUR, cur_range)
        dates = self.get_dates(cur_range)

        operations = defaultdict(list)
        for order in money_orders:
            if order.cur == self.RUB:
                c = 1
            elif order.cur == self.USD:
                c = usd[order.date]
            elif order.cur == self.EUR:
                c = eur[order.date]
            else:
                raise ValueError(order.cur)
            operations[order.date].append(c * order.sum)

        prev_price = {}
        cash = ValueList('cbr')
        rate = CBR_BASE_RATE
        s = prev = proc = 0
        for date in dates:
            s += builtins.sum(operations[date])
            rate = CBR_RATE.get(date, rate)
            pr = rate / 100 / 365.5
            proc += proc * pr
            proc += prev * pr

            if date in usd:
                prev_price[self.USD] = usd[date]
            if date in eur:
                prev_price[self.EUR] = eur[date]

            if date >= time_range.start:
                if currency == self.USD:
                    c3 = usd.get(date, prev_price[self.USD])
                elif currency == self.EUR:
                    c3 = eur.get(date, prev_price[self.EUR])
                else:
                    c3 = 1

                day_value = Value()
                day_value.key = date
                day_value.value = (s + proc) / c3
                cash.append(day_value)

            prev = s
        return cash

    def get_dates(self, time_range):
        date = time_range.start_time
        while date < time_range.end_time:
            yield date_to_key(date)
            date += timedelta(days=1)

    def _get_history(self, manager, time_range, currency):
        cash = ValueList(manager.collection)
        orders_range = TimeRange(None, time_range.end_time)
        orders = manager.get_data(self.portfolio_id, orders_range,
                                  broker_id=self.broker_id)
        money_orders = MoneyManagerCached.get_data(
            self.portfolio_id, orders_range, broker_id=self.broker_id)

        if not orders:
            dates_range = TimeRange(
                key_to_date(max(money_orders[0].date, time_range.start)),
                time_range.end_time)
            dates = self.get_dates(dates_range)
            for date in dates:
                day_value = Value()
                day_value.key = date
                day_value.value = float(0)
                cash.append(day_value)
            return cash

        dates_range = TimeRange(
            key_to_date(min(orders[0].date, money_orders[0].date)),
            time_range.end_time)
        dates = self.get_dates(dates_range)

        cur_range = TimeRange(key_to_date(orders[0].date),
                              time_range.end_time)
        usd = QuotesManager.get_quotes(self.USD, cur_range)
        eur = QuotesManager.get_quotes(self.EUR, cur_range)

        operations = defaultdict(list)
        for order in orders:
            if order.cur not in self.CURRENCIES:
                raise ValueError(order.cur)
            operations[order.date].append(order)

        prev_price = {}
        s = 0
        for date in dates:
            if date in usd:
                prev_price[self.USD] = usd[date]
            if date in eur:
                prev_price[self.EUR] = eur[date]

            day_sum = 0
            for order in operations[date]:
                c1 = c2 = 1
                if order.cur == self.USD:
                    c1 = usd.get(date, prev_price[self.USD])
                elif order.cur == self.EUR:
                    c1 = eur.get(date, prev_price[self.EUR])

                if currency == self.USD:
                    c2 = usd.get(date, prev_price[self.USD])
                elif currency == self.EUR:
                    c2 = eur.get(date, prev_price[self.EUR])
                day_sum += order.sum * c1 / c2
            s += day_sum

            if date < time_range.start:
                continue

            day_value = Value()
            day_value.key = date
            day_value.value = float(s)
            cash.append(day_value)
        return cash

    def get_cash_history(self, time_range, currency=RUB):
        return self._get_history(MoneyManagerCached, time_range, currency)

    def get_dividend_history(self, time_range, currency=RUB):
        return self._get_history(DividendManager, time_range, currency)

    def get_commission_history(self, time_range, currency=RUB):
        return self._get_history(CommissionManager, time_range, currency)

    def get_fund_history(self, cash_data, fund, currency=RUB):
        cur_range = TimeRange(key_to_date(cash_data[0].key),
                              key_to_date(cash_data[-1].key))
        quotes = QuotesManager.get_quotes(fund, cur_range)
        prev_price = prev_value = c = 0
        history = ValueList(fund)

        for cash_day in cash_data:
            if cash_day.key in quotes:
                prev_price = price = quotes[cash_day.key]
            else:
                price = prev_price

            if abs(cash_day.value - prev_value) > 0:
                c += (cash_day.value - prev_value)/price
            prev_value = cash_day.value

            day_value = Value()
            day_value.key = cash_day.key
            day_value.value = price * c
            history.append(day_value)
        return history

    def add_charts(self, *args, step=10000):
        assert args
        figure = plt.figure()
        ax = figure.add_subplot()

        t = range(len(args[0]))
        d1 = args[0][0].key
        d2 = args[0][-1].key
        minv = None
        maxv = None

        legend = []
        plots = []
        for data in args:
            assert len(data) == len(args[0])
            plot = ax.plot(t, data)[0]
            plots.append(plot)
            value = str(round(data[-1].value, 2))
            ax.text(t[-1], data[-1].value, value)
            legend.append(data.title)
            minv = data.min if minv is None else min(minv, data.min)
            maxv = data.max if maxv is None else max(maxv, data.max)

        step = int(step)
        sub_ste = int(step / 5)
        minv = int(minv)
        maxv = int(maxv)
        if minv < 0:
            major_ticks = list(range(0, minv, -step))
            major_ticks.extend(range(0, maxv, step))
            minor_ticks = list(range(0, minv - sub_ste, -sub_ste))
            minor_ticks.extend(range(0, maxv + sub_ste, sub_ste))
        else:
            major_ticks = range(minv, maxv, step)
            minor_ticks = range(minv - sub_ste, maxv + sub_ste, sub_ste)

        ax.set_yticks(major_ticks)
        ax.set_yticks(minor_ticks, minor=True)

        ax.grid(which='minor', alpha=0.5)
        ax.grid(which='major', alpha=0.8)
        ax.legend(plots, legend)
        ax.set_title(f'{d1[0]}-{d1[1]}-{d1[2]} - {d2[0]}-{d2[1]}-{d2[2]}')

    def show_charts(self):
        plt.show()
