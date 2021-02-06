from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING

from portfolio.config import MONGO_URL


_CLIENT = None


def get_client():
    global _CLIENT
    if not _CLIENT:
        _CLIENT = MongoClient(MONGO_URL)
    return _CLIENT


def date_to_key(date):
    return date.year, date.month, date.day


def key_to_date(date):
    return datetime(date[0], date[1], date[2])


def sround(s):
    return round(s, 2)


class Value:
    __slots__ = ('key', 'value')

    def __float__(self):
        return self.value

    def copy(self):
        value = Value()
        value.key = self.key
        value.value = self.value
        return value


class ValueList(list):
    def __init__(self, title):
        super(ValueList, self).__init__()
        self.i = 0
        self.title = title
        self._min = None
        self._max = None

    def append(self, object):
        if self._min is None or object.value < self._min:
            self._min = object.value
        if self._max is None or object.value > self._max:
            self._max = object.value
        super().append(object)

    @property
    def min(self):
        return self._min

    @property
    def max(self):
        return self._max

    def __add__(self, other):
        assert isinstance(other, ValueList)
        result = ValueList(f'{self.title}+{other.title}')
        if not other:
            for item in self:
                result.append(item.copy())

        for item1, item2 in zip(self, other):
            if item1.key != item2.key:
                raise ValueError('inconsistent lists')
            value = Value()
            value.key = item1.key
            value.value = item1.value + item2.value
            result.append(value)
        return result

    def __sub__(self, other):
        assert isinstance(other, ValueList)
        result = ValueList(f'{self.title}-{other.title}')
        if not other:
            for item in self:
                result.append(item.copy())

        for item1, item2 in zip(self, other):
            if item1.key != item2.key:
                raise ValueError('inconsistent lists')
            value = Value()
            value.key = item1.key
            value.value = item1.value - item2.value
            result.append(value)
        return result

    def __truediv__(self, other):
        assert isinstance(other, ValueList)
        result = ValueList(f'{self.title}/{other.title}')
        if not other:
            for item in self:
                result.append(item.copy())

        for item1, item2 in zip(self, other):
            if item1.key != item2.key:
                raise ValueError('inconsistent lists')
            value = Value()
            value.key = item1.key
            value.value = sround(item1.value / item2.value)
            result.append(value)
        return result

    def __rmul__(self, other):
        assert isinstance(other, (int, float))
        result = ValueList(f'{other}*{self.title}')
        for item1 in self:
            value = Value()
            value.key = item1.key
            value.value = other * item1.value
            result.append(value)
        return result

    def keys(self):
        for i in range(len(self)):
            yield key_to_date(self[i].key)

    def values(self):
        for i in range(len(self)):
            yield self[i].value


class TimeRange:
    def __init__(self, start_time, end_time):
        if start_time:
            assert isinstance(start_time, datetime)
            start_time = start_time.replace(hour=0, minute=0, second=0)
        if end_time:
            assert isinstance(end_time, datetime)
            end_time = end_time.replace(hour=23, minute=59, second=59)
        self.start_time = start_time
        self.end_time = end_time
        self.start = date_to_key(start_time) if start_time else None
        self.end = date_to_key(end_time) if end_time else None


class DBManager:
    collection = model = None

    @classmethod
    def upsert(cls, key, data=None):
        assert isinstance(key, dict)
        data = data or key
        assert isinstance(data, dict)

        client = get_client()
        db = client.market
        response = db[cls.collection].update(key, {'$set': data},
                                             upsert=True)
        return response

    @classmethod
    def insert(cls, data=None):
        client = get_client()
        db = client.market
        if isinstance(data, dict):
            for key in data:
                if not hasattr(cls.model, key):
                    raise ValueError(f'unknown field {key}')
            db[cls.collection].insert(data)
        if isinstance(data, list):
            for key in data[0]:
                if not hasattr(cls.model, key):
                    raise ValueError(f'unknown field {key}')
            db[cls.collection].insert_many(data)

    @classmethod
    def clear(cls):
        client = get_client()
        db = client.market
        db[cls.collection].drop()

    @classmethod
    def get(cls, **kwargs):
        sort = kwargs.pop('sort', None)
        first = kwargs.pop('first', False)
        fields = kwargs.pop('fields', {})
        for key in list(kwargs.keys()):
            value = kwargs[key]
            if isinstance(value, TimeRange):
                if value.start_time and value.end_time:
                    kwargs[key] = {'$gte': value.start_time,
                                   '$lte': value.end_time}
                elif value.start_time and not value.end_time:
                    kwargs[key] = {'$gte': value.start_time}
                elif not value.start_time and value.end_time:
                    kwargs[key] = {'$lte': value.end_time}
                else:
                    kwargs.pop(key)

        if sort and not isinstance(sort, list):
            sort = [sort]

        client = get_client()
        db = client.market
        if first:
            response = db[cls.collection].find_one(kwargs)
        else:
            if fields:
                response = db[cls.collection].find(kwargs, fields)
            else:
                response = db[cls.collection].find(kwargs)
        if sort:
            response = response.sort([
                (field[0], ASCENDING if field[1] >= 0 else DESCENDING)
                if isinstance(field, tuple) else (field, ASCENDING)
                for field in sort])
        return response
