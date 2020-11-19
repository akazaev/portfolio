from functools import lru_cache
import builtins

from base import date_to_key, key_to_date
from collections import defaultdict, OrderedDict
from datetime import datetime, timedelta

import matplotlib.pyplot as plt

from base import TimeRange
from config import CBR_RATE, CBR_BASE_RATE
from managers import (
    QuotesManager, OrdersManager, MoneyManager, SecuritiesManager,
    Order, Money)


class Portfolio:
    RUB = 'RUB'
    USD = 'USD'
    EUR = 'EUR'

    def __init__(self, portfolio_id):
        self.portfolio_id = portfolio_id

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

    def current_value(self):
        pass

    def chart_cbr(self, start_date, end_date):
        assert isinstance(start_date, datetime)
        assert isinstance(end_date, datetime)
        start_date = start_date.replace(hour=0, minute=0, second=0)
        end_date = end_date.replace(hour=23, minute=59, second=59)
        time_range = TimeRange(start_date, end_date)

        data = self.get_value_history(time_range)
        cbr_data = self.get_cbr_history(time_range)
        cash_data = self.get_cash_history(time_range)

        assert len(data) == len(cbr_data)
        assert len(data) == len(cash_data)

        self.show_charts(data, cbr_data, cash_data)
        #self.show_charts(cash_data, cbr_data)
        #self.show_charts(cash_data)

    def get_value_history(self, time_range):
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
        stock_orders = OrdersManager.get_orders(self.portfolio_id,
                                                orders_range)
        money_orders = MoneyManager.get_operations(self.portfolio_id,
                                                   orders_range)
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

            value[date] = portfolio_sum
        return value

    def get_cbr_history(self, time_range):
        money_range = TimeRange(None, time_range.end_time)
        money_orders = MoneyManager.get_operations(self.portfolio_id,
                                                   money_range)
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

        cash = OrderedDict()
        rate = CBR_BASE_RATE
        s = prev = proc = 0
        for date in dates:
            s += builtins.sum(operations[date])

            rate = CBR_RATE.get(date, rate)
            pr = rate / 100 / 365.5
            proc += prev * pr
            if date >= time_range.start:
                cash[date] = s + proc
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

    def get_cash_history(self, time_range):
        money_range = TimeRange(None, time_range.end_time)
        money_orders = MoneyManager.get_operations(self.portfolio_id,
                                                   money_range)
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

        cash = OrderedDict()
        s = 0
        for date in dates:
            s += builtins.sum(operations[date])
            if date < time_range.start:
                continue

            cash[date] = s
        return cash

    def show_charts(self, *args):
        assert args
        fig, ax = plt.subplots()
        t = range(len(args[0]))

        d1 = next(iter(args[0]))
        d2 = next(reversed(args[0]))

        for data in args:
            ax.plot(t, data.values())

        ax.grid()
        ax.set_title(f'{d1[0]}-{d1[1]}-{d1[2]} - {d2[0]}-{d2[1]}-{d2[2]}')
        plt.show()
