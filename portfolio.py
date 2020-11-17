from collections import namedtuple
from functools import lru_cache
import builtins

from collections import defaultdict, OrderedDict
from datetime import datetime, timedelta

import matplotlib.pyplot as plt

from base import DBManager, TimeRange
from config import CBR_RATE, CBR_BASE_RATE


def date_to_key(date):
    #return date.strftime('%Y-%m-%d')
    return date.year, date.month, date.day


def key_to_date(date):
    return datetime(date[0], date[1], date[2])


class QuotesManager(DBManager):
    collection = 'quotes'

    @classmethod
    @lru_cache(maxsize=None)
    def get_quotes(cls, isin, time_range):
        data = cls.get(isin=isin, time=time_range, sort='time',
                       fields={'time': 1, 'price': 1})
        result = OrderedDict()
        for record in data:
            result[date_to_key(record['time'])] = record['price']
        return result


Money = namedtuple('Operation', ['date', 'cur', 'sum'])


class MoneyManager(DBManager):
    collection = 'money'

    @classmethod
    @lru_cache(maxsize=None)
    def get_operations(cls, portfolio_id, time_range):
        data = cls.get(portfolio=portfolio_id, date=time_range, sort='time')
        data = [Money(date=date_to_key(row['date']), cur=row['cur'],
                      sum=row['sum']) for row in data]
        return data


Order = namedtuple('Order', ['date', 'isin', 'quantity', 'sum', 'cur'])


class OrdersManager(DBManager):
    collection = 'orders'
    model = Order

    @classmethod
    @lru_cache(maxsize=None)
    def get_orders(cls, portfolio_id, time_range):
        data = cls.get(portfolio=portfolio_id, date=time_range, sort='time')
        data = [cls.model(date=date_to_key(row['date']), isin=row['isin'],
                          quantity=row['quantity'], sum=row['sum'],
                          cur=row['cur'])
                for row in data]
        return data


class SecuritiesManager(DBManager):
    collection = 'securities'

    @classmethod
    @lru_cache(maxsize=None)
    def get_securities(cls, isin):
        data = cls.get(isin=isin, first=True)
        assert data
        return {'cur': data['currency']}


class Portfolio:
    RUB = 'RUB'
    USD = 'USD'
    EUR = 'EUR'

    def __init__(self, portfolio_id):
        self.portfolio_id = portfolio_id

    def chart_cbr(self, start_date, end_date):
        assert isinstance(start_date, datetime)
        assert isinstance(end_date, datetime)
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

        usd = QuotesManager.get_quotes('USD', time_range)
        eur = QuotesManager.get_quotes('EUR', time_range)

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
        start_date = date_to_key(time_range.start_time)

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

            if date < start_date:
                continue

            if date in usd:
                prev_price['usd'] = usd[date]
            if date in eur:
                prev_price['eur'] = eur[date]

            portfolio_sum = 0
            for key, quantity in portfolio.items():
                isin, cur = key
                if isin == self.RUB:
                    portfolio_sum += quantity
                elif isin == self.USD:
                    if date in usd:
                        c = usd[date]
                    else:
                        c = prev_price['usd']
                    portfolio_sum += c * quantity
                elif isin == self.EUR:
                    if date in eur:
                        c = eur[date]
                    else:
                        c = prev_price['eur']
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

                    cur = SecuritiesManager.get_securities(isin=isin)['cur']

                    if cur == self.RUB:
                        c2 = 1
                    elif cur == self.USD:
                        if date in usd:
                            c2 = usd[date]
                        else:
                            c2 = prev_price['usd']
                    elif cur == self.EUR:
                        if date in eur:
                            c2 = eur[date]
                        else:
                            c2 = prev_price['eur']
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
        usd = QuotesManager.get_quotes('USD', cur_range)
        eur = QuotesManager.get_quotes('EUR', cur_range)

        dates = self.get_dates(cur_range)
        start_date = date_to_key(time_range.start_time)

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
            if date >= start_date:
                cash[date] = s + proc
            proc += proc * pr
            prev = s
        return cash

    def get_cbr_history2(self, time_range):
        cash = self.get_cash_history(time_range)
        dates = self.get_dates(time_range)

        rate = CBR_BASE_RATE
        bank = OrderedDict()
        prev = cash[dates[0]]
        bank[dates[0]] = prev
        proc = 0
        for day in dates[1:]:
            rate = CBR_RATE.get(day, rate)
            pr = rate / 100 / 365.5
            proc += prev * pr
            if money_orders[0].date >= date:
                bank[day] = cash[day] + proc
            proc += proc * pr
            prev = cash[day]
        return bank

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
        usd = QuotesManager.get_quotes('USD', cur_range)
        eur = QuotesManager.get_quotes('EUR', cur_range)

        dates = self.get_dates(cur_range)
        start_date = date_to_key(time_range.start_time)

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
            if date < start_date:
                continue

            cash[date] = s
        return cash

    def show_charts(self, *args):
        assert args
        fig, ax = plt.subplots()
        t = range(len(args[0]))

        for data in args:
            ax.plot(t, data.values())

        ax.grid()
        plt.show()
