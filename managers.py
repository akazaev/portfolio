from datetime import timedelta
from collections import OrderedDict, namedtuple
from functools import lru_cache

from base import DBManager, date_to_key, TimeRange
from loaders import QuotesLoader


class QuotesManager(DBManager):
    collection = 'quotes'

    @classmethod
    @lru_cache(maxsize=None)
    def get_quotes(cls, isin, time_range):
        data = cls.get(isin=isin, time=time_range, sort='time',
                       fields={'time': 1, 'price': 1})
        result = OrderedDict()
        last = None
        for record in data:
            result[date_to_key(record['time'])] = record['price']
            last = record
        last_date = last['time'] if last else time_range.start_time
        if date_to_key(last_date) < time_range.end:
            if last is not None:
                last_date += timedelta(days=1)
            time_range = TimeRange(last_date, time_range.end_time)
            data = QuotesLoader.load(isin, time_range)
            for record in data:
                if date_to_key(record['time']) > time_range.end:
                    break
                result[date_to_key(record['time'])] = record['price']
                last = record
        assert date_to_key(last['time']) == time_range.end
        return result


Money = namedtuple('Money', ['date', 'cur', 'sum'])


class MoneyManager(DBManager):
    collection = 'money'
    model = Money

    @classmethod
    @lru_cache(maxsize=None)
    def get_operations(cls, portfolio_id, time_range):
        data = cls.get(portfolio=portfolio_id, date=time_range, sort='time')
        data = [cls.model(date=date_to_key(row['date']), cur=row['cur'],
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
                          cur=row['cur']) for row in data]
        return data


class SecuritiesManager(DBManager):
    collection = 'securities'
    by_ticker = {
        'USD': 'USD000UTSTOM',
        'EUR': 'EUR_RUB__TOM',
    }

    @classmethod
    @lru_cache(maxsize=None)
    def get_securities(cls, isin):
        if isin in cls.by_ticker:
            data = cls.get(ticker=cls.by_ticker[isin], first=True)
        else:
            data = cls.get(isin=isin, first=True)
        assert data
        return data
