from datetime import datetime

import requests

from config import API_URL, API_TOKEN


class QuotesLoader:
    @classmethod
    def load(cls, isin, time_range, interval='day'):
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
                  'interval': interval}, headers=headers)

        data_save = []
        for day in response.json()['payload']['candles']:
            time = datetime.strptime(day['time'], '%Y-%m-%dT%H:%M:%SZ')
            price = float(day['c'])
            record = {
                'time': time,
                'price': price,
                'isin': isin.upper(),
                'figi': figi.upper(),
                'interval': interval,
            }
            data_save.append(record)
        return data_save
