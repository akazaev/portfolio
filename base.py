from datetime import datetime
from pymongo import MongoClient, ASCENDING

from config import MONGO_URL


_CLIENT = None


def get_client():
    global _CLIENT
    if not _CLIENT:
        client = MongoClient(MONGO_URL)
        _CLIENT = client
    return _CLIENT


def date_to_key(date):
    return date.year, date.month, date.day


def key_to_date(date):
    return datetime(date[0], date[1], date[2])


class TimeRange:
    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time
        self.start = date_to_key(start_time) if start_time else None
        self.end = date_to_key(end_time) if end_time else None


class DBManager:
    collection = mode = None

    @classmethod
    def upsert(cls, key, data=None):
        assert isinstance(key, dict)
        data = data or key
        assert isinstance(data, dict)
        with get_client() as client:
            db = client.market
            response = db[cls.collection].update(key, {'$set': data},
                                                 upsert=True)
            if response.get('nModified'):
                print(data)

    @classmethod
    def insert(cls, data=None):
        with get_client() as client:
            db = client.market
            if isinstance(data, dict):
                db[cls.collection].insert(data)
            if isinstance(data, list):
                db[cls.collection].insert_many(data)

    @classmethod
    def clear(cls):
        with get_client() as client:
            db = client.market
            db[cls.collection].drop()

    @classmethod
    def get(cls, **kwargs):
        sort = kwargs.pop('sort', None)
        first = kwargs.pop('first', False)
        fields = kwargs.pop('fields', {})
        for key, value in kwargs.items():
            if isinstance(value, TimeRange):
                if value.start_time and value.end_time:
                    kwargs[key] = {'$gte': value.start_time,
                                   '$lte': value.end_time}
                if value.start_time and not value.end_time:
                    kwargs[key] = {'$gte': value.start_time}
                if not value.start_time and value.end_time:
                    kwargs[key] = {'$lte': value.end_time}

        if sort and not isinstance(sort, list):
            sort = [sort]
        with get_client() as client:
            db = client.market
            if first:
                response = db[cls.collection].find_one(kwargs)
            else:
                if fields:
                    response = db[cls.collection].find(kwargs, fields)
                else:
                    response = db[cls.collection].find(kwargs)
            if sort:
                response = response.sort([(field, ASCENDING)
                                          for field in sort])
            return response
