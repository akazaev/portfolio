from datetime import datetime

import requests

from portfolio.config import API_URL, API_TOKEN, ISS_API_URL


class QuotesLoader:
    @classmethod
    def history(cls, isin, time_range, interval='day'):
        from portfolio.managers import SecuritiesManager
        data = SecuritiesManager.get_data(isin=isin)
        figi = data['figi']
        headers = {'Authorization': f'Bearer {API_TOKEN}'}

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

    @classmethod
    def _get_iss_data(cls, code):
        url = f'{ISS_API_URL}/iss/engines/currency/markets/selt/' \
              f'boards/CETS/securities/%s.json'
        response = requests.get(url % code)
        data = response.json()['marketdata']
        last = data['data'][0][data['columns'].index('LAST')]
        status = data['data'][0][data['columns'].index('TRADINGSTATUS')]
        # status: N, T
        return last, status == 'T'

    @classmethod
    def _get_broker_data(cls, isin):
        from portfolio.managers import SecuritiesManager
        data = SecuritiesManager.get_data(isin=isin)
        figi = data['figi']
        headers = {'Authorization': f'Bearer {API_TOKEN}'}

        response = requests.get(API_URL + '/market/orderbook',
                                data={'figi': figi, 'depth': 0},
                                headers=headers)
        return response.json()['payload']['lastPrice']

    @classmethod
    def current(cls, isin):
        currencies = {
            'USD': ('USD000000TOD', 'USD000UTSTOM', ),
            'EUR': ('EUR_RUB__TOD', 'EUR_RUB__TOM',),
        }
        if isin in currencies:
            last, _active = cls._get_iss_data(currencies[isin][0])
            if not _active:
                last, _active = cls._get_iss_data(currencies[isin][1])
        else:
            last = cls._get_broker_data(isin)
        return last
