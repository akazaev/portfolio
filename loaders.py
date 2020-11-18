from datetime import datetime

import requests

from base import DBManager
from config import API_URL, API_TOKEN


class QuotesLoader(DBManager):
    collection = 'quotes'

    @classmethod
    def load(cls, isin, time_range):
        from managers import SecuritiesManager
        data = SecuritiesManager.get_securities(isin=isin)
        figi = data['figi']

        headers = {
            'Authorization': f'Bearer {API_TOKEN}'
        }

        frmt = '%Y-%m-%dT00:00:00.000000+03:00'
        from_time = time_range.start_time.strftime(frmt)
        frmt = '%Y-%m-%dT23:59:59.000000+03:00'
        to_time = time_range.end_time.strftime(frmt)

        response = requests.get(
            API_URL + '/market/candles',
            data={'figi': figi, 'from': from_time, 'to': to_time,
                  'interval': 'day'}, headers=headers)

        for day in response.json()['payload']['candles']:
            time = datetime.strptime(day['time'], '%Y-%m-%dT%H:%M:%SZ')
            price = float(day['c'])
            data_save = {
                'time': time,
                'price': price,
                'isin': isin.upper(),
                'figi': figi.upper(),
            }
            cls.upsert(data_save, data_save)
            yield {'time': time, 'price': price}
