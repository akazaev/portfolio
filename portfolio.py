from functools import lru_cache
import builtins

from base import date_to_key, key_to_date
from collections import defaultdict, OrderedDict
from datetime import datetime, timedelta

import matplotlib.pyplot as plt

from base import TimeRange
from config import CBR_RATE, CBR_BASE_RATE
from loaders import QuotesLoader
from managers import (
    QuotesManager, OrdersManager, MoneyManager, SecuritiesManager,
    Order, Money)


class Portfolio:
    RUB = 'RUB'
    USD = 'USD'
    EUR = 'EUR'

    def __init__(self, portfolio_id, broker_id=None):
        self.portfolio_id = portfolio_id
        self.broker_id = broker_id

    def cbr(self, start_date, end_date):
        assert isinstance(start_date, datetime)
        assert isinstance(end_date, datetime)
        end_date = end_date.replace(hour=23, minute=59, second=59)
        time_range = TimeRange(start_date, end_date)

        data = self.get_value_history(time_range)
        cbr_data = self.get_cbr_history(time_range)
        cash_data = self.get_cash_history(time_range)

        assert len(data) == len(cbr_data)
        assert len(data) == len(cash_data)

    def chart_cbr(self, start_date, end_date, currency=RUB):
        assert isinstance(start_date, datetime)
        assert isinstance(end_date, datetime)
        start_date = start_date.replace(hour=0, minute=0, second=0)
        end_date = end_date.replace(hour=23, minute=59, second=59)
        time_range = TimeRange(start_date, end_date)

        data = self.get_value_history(time_range, currency=currency)
        cbr_data = self.get_cbr_history(time_range, currency=currency)
        cash_data = self.get_cash_history(time_range, currency=currency)

        assert len(data) == len(cbr_data)
        assert len(data) == len(cash_data)

        self.show_charts(data, cbr_data, cash_data)

    def chart_profit(self, start_date, end_date, currency=RUB):
        assert isinstance(start_date, datetime)
        assert isinstance(end_date, datetime)
        start_date = start_date.replace(hour=0, minute=0, second=0)
        end_date = end_date.replace(hour=23, minute=59, second=59)
        time_range = TimeRange(start_date, end_date)

        data = self.get_value_history(time_range, currency=currency)
        cbr_data = self.get_cbr_history(time_range, currency=currency)
        cash_data = self.get_cash_history(time_range, currency=currency)

        assert len(data) == len(cbr_data)
        assert len(data) == len(cash_data)

        for day in cash_data:
            data[day] -= cash_data[day]
            cbr_data[day] -= cash_data[day]

        self.show_charts(data, cbr_data)

    def get_value_history(self, time_range, currency=RUB):
        changes = {
            'JE00B5BCW814': 'RU000A1025V3',
            'je00b5bcw814': 'ru000a1025v3',
        }

        usd = QuotesManager.get_quotes(self.USD, time_range)
        eur = QuotesManager.get_quotes(self.EUR, time_range)

        value = {}
        prev_price = {}

        portfolio = defaultdict(int)
        operations = defaultdict(list)
        orders_range = TimeRange(None, time_range.end_time)
        stock_orders = OrdersManager.get_orders(
            self.portfolio_id, orders_range, broker_id=self.broker_id)
        money_orders = MoneyManager.get_operations(
            self.portfolio_id, orders_range, broker_id=self.broker_id)
        all_orders = stock_orders + money_orders
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

            for order in day_orders:
                cur = order.cur
                sum = order.sum
                if isinstance(order, Order):
                    isin = order.isin
                    quantity = order.quantity
                    if isin in changes and changes[isin] in portfolio:
                        portfolio[(isin, cur)] = portfolio.pop(
                            (changes[isin], cur))
                    portfolio[(isin, cur)] += quantity
                    portfolio[(cur, cur)] -= quantity / abs(quantity) * sum
                if isinstance(order, Money):
                    portfolio[(cur, cur)] += sum

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

                    security = SecuritiesManager.get_securities(isin=isin)
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

            value[date] = portfolio_sum / c3
        return value

    def get_value(self):
        changes = {
            'JE00B5BCW814': 'RU000A1025V3',
            'je00b5bcw814': 'ru000a1025v3',
        }

        usd = QuotesLoader.current(self.USD)
        eur = QuotesLoader.current(self.EUR)

        orders_range = TimeRange(None, datetime.now())
        stock_orders = OrdersManager.get_orders(
            self.portfolio_id, orders_range, broker_id=self.broker_id)
        money_orders = MoneyManager.get_operations(
            self.portfolio_id, orders_range, broker_id=self.broker_id)
        all_orders = stock_orders + money_orders
        all_orders.sort(key=lambda x: x[0])

        portfolio = defaultdict(int)

        for order in all_orders:
            cur = order.cur
            sum = order.sum
            if isinstance(order, Order):
                isin = order.isin
                quantity = order.quantity
                portfolio[(isin, cur)] += quantity
                portfolio[(cur, cur)] -= quantity / abs(quantity) * sum
            if isinstance(order, Money):
                portfolio[(cur, cur)] += sum

        portfolio_sum = 0
        for key, quantity in portfolio.items():
            isin, cur = key
            if isin == self.RUB:
                portfolio_sum += quantity
            elif isin == self.USD:
                c = usd
                portfolio_sum += c * quantity
            elif isin == self.EUR:
                c = eur
                portfolio_sum += c * quantity
            else:
                if isin in changes:
                    isin = changes[isin]
                c1 = QuotesLoader.current(isin)

                security = SecuritiesManager.get_securities(isin=isin)
                cur = security['currency']

                if cur == self.RUB:
                    c2 = 1
                elif cur == self.USD:
                    c2 = usd
                elif cur == self.EUR:
                    c2 = eur
                else:
                    raise ValueError(cur)

                portfolio_sum += c1 * c2 * quantity
        return portfolio_sum

    def get_cbr_history(self, time_range, currency=RUB):
        money_range = TimeRange(None, time_range.end_time)
        money_orders = MoneyManager.get_operations(
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
        cash = OrderedDict()
        rate = CBR_BASE_RATE
        s = prev = proc = 0
        for date in dates:
            s += builtins.sum(operations[date])
            rate = CBR_RATE.get(date, rate)
            pr = rate / 100 / 365.5
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

                cash[date] = (s + proc) / c3
            proc += proc * pr
            prev = s
        return cash

    @lru_cache(maxsize=None)
    def get_dates(self, time_range):
        dates = []
        date = time_range.start_time
        while date < time_range.end_time:
            dates.append(date_to_key(date))
            date += timedelta(days=1)
        return dates

    def get_cash_history(self, time_range, currency=RUB):
        money_range = TimeRange(None, time_range.end_time)
        money_orders = MoneyManager.get_operations(
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
        cash = OrderedDict()
        s = 0
        for date in dates:
            s += builtins.sum(operations[date])

            if date in usd:
                prev_price[self.USD] = usd[date]
            if date in eur:
                prev_price[self.EUR] = eur[date]

            if date < time_range.start:
                continue

            if currency == self.USD:
                c3 = usd.get(date, prev_price[self.USD])
            elif currency == self.EUR:
                c3 = eur.get(date, prev_price[self.EUR])
            else:
                c3 = 1

            cash[date] = s / c3
        return cash

    def show_charts(self, *args):
        assert args
        fig, ax = plt.subplots()
        t = range(len(args[0]))

        d1 = next(iter(args[0]))
        d2 = next(reversed(args[0]))
        print(args[0][d2])

        for data in args:
            if isinstance(data, dict):
                data = data.values()
            ax.plot(t, data)

        ax.grid()
        ax.set_title(f'{d1[0]}-{d1[1]}-{d1[2]} - {d2[0]}-{d2[1]}-{d2[2]}')
        plt.show()
