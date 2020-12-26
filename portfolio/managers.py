from datetime import datetime, timedelta
from collections import OrderedDict, namedtuple
from functools import lru_cache

from portfolio.base import DBManager, date_to_key, TimeRange
from portfolio.loaders import QuotesLoader


class QuotesManager(DBManager):
    collection = 'quotes'

    @classmethod
    @lru_cache(maxsize=None)
    def get_quotes(cls, isin, time_range):
        today = date_to_key(datetime.now())
        new_range = time_range
        if time_range.end == today:
            pre = time_range.end_time - timedelta(days=1)
            new_range = TimeRange(time_range.start_time, pre)

        data = cls.get(isin=isin, time=new_range, sort='time',
                       fields={'time': 1, 'price': 1})
        result = OrderedDict()
        last = None
        for record in data:
            result[date_to_key(record['time'])] = record['price']
            last = record
        last_date = last['time'] if last else time_range.start_time

        if date_to_key(last_date) < new_range.end:
            if last is not None:
                last_date += timedelta(days=1)
                last_date = last_date.replace(hour=0, minute=0, second=0)
            new_range = TimeRange(last_date, new_range.end_time)
            data = QuotesLoader.history(isin, new_range)
            if data:
                cls.insert(data)
                for record in data:
                    if date_to_key(record['time']) > new_range.end:
                        break
                    result[date_to_key(record['time'])] = record['price']

        if time_range.end == today:
            price = QuotesLoader.current(isin)
            result[today] = price

        return result


Money = namedtuple('Money', ['date', 'cur', 'sum', 'portfolio', 'broker'])


class MoneyManager(DBManager):
    collection = 'money'
    model = Money

    @classmethod
    @lru_cache(maxsize=None)
    def get_data(cls, portfolio_id=None, time_range=None, broker_id=None):
        filters = {'sort': 'time'}
        if broker_id:
            filters['broker'] = broker_id
        if portfolio_id:
            filters['portfolio'] = portfolio_id
        if time_range:
            filters['date'] = time_range
        data = cls.get(**filters)
        data = [cls.model(date=date_to_key(row['date']), cur=row['cur'],
                          sum=row['sum'], portfolio=row['portfolio'],
                          broker=row['broker']) for row in data]
        return data


Order = namedtuple('Order', ['date', 'isin', 'quantity', 'sum', 'cur',
                             'portfolio', 'broker'])


class OrdersManager(DBManager):
    collection = 'orders'
    model = Order

    @classmethod
    @lru_cache(maxsize=None)
    def get_data(cls, portfolio_id=None, time_range=None, broker_id=None):
        filters = {'sort': 'time'}
        if broker_id:
            filters['broker'] = broker_id
        if portfolio_id:
            filters['portfolio'] = portfolio_id
        if time_range:
            filters['date'] = time_range
        data = cls.get(**filters)
        data = [cls.model(date=date_to_key(row['date']), isin=row['isin'],
                          quantity=row['quantity'], sum=row['sum'],
                          cur=row['cur'], portfolio=row['portfolio'],
                          broker=row['broker']) for row in data]
        return data


class SecuritiesManager(DBManager):
    collection = 'securities'
    by_ticker = {
        'USD': 'USD000UTSTOM',
        'EUR': 'EUR_RUB__TOM',
    }

    @classmethod
    @lru_cache(maxsize=None)
    def get_data(cls, isin):
        if isin in cls.by_ticker:
            data = cls.get(ticker=cls.by_ticker[isin], first=True)
        else:
            data = cls.get(isin=isin, first=True)
        assert data
        return data


Dividend = namedtuple('Dividend', ['date', 'cur', 'sum'])


class DividendManager(DBManager):
    collection = 'dividends'
    model = Dividend

    @classmethod
    @lru_cache(maxsize=None)
    def get_data(cls, portfolio_id=None, time_range=None, broker_id=None):
        filters = {'sort': 'time'}
        if broker_id:
            filters['broker'] = broker_id
        if portfolio_id:
            filters['portfolio'] = portfolio_id
        if time_range:
            filters['date'] = time_range
        data = cls.get(**filters)
        data = [cls.model(date=date_to_key(row['date']), cur=row['cur'],
                          sum=row['sum']) for row in data]
        return data


Commission = namedtuple('Commission', ['date', 'cur', 'sum'])


class CommissionManager(DBManager):
    collection = 'commission'
    model = Commission

    @classmethod
    @lru_cache(maxsize=None)
    def get_data(cls, portfolio_id=None, time_range=None, broker_id=None):
        filters = {'sort': 'time'}
        if broker_id:
            filters['broker'] = broker_id
        if portfolio_id:
            filters['portfolio'] = portfolio_id
        if time_range:
            filters['date'] = time_range
        data = cls.get(**filters)
        data = [cls.model(date=date_to_key(row['date']), cur=row['cur'],
                          sum=row['sum']) for row in data]
        return data
