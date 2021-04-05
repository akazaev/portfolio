from datetime import datetime
from itertools import chain

import xml.etree.ElementTree as etree

from portfolio.managers import (
    Order, Dividend, DividendManager, Commission, CommissionManager,
    Money, MoneyManager, OrdersManager, SecuritiesManager)
from portfolio.portfolio import Portfolio


class Parser:
    BROKER = None

    def __init__(self, portfolio):
        self.portfolio = {'portfolio': portfolio, 'broker': self.BROKER}

    @classmethod
    def get_child(cls, root, child_tag):
        for child in root:
            if child_tag in child.tag:
                return child
        raise ValueError('not found')

    @classmethod
    def get(cls, root, *names):
        if len(names) == 1:
            names = names[0]
            names = names.split('.')
        for name in names:
            root = cls.get_child(root, name)
            if root is None:
                raise ValueError('not found')
        return root

    @classmethod
    def get_silent(cls, root, *names):
        try:
            return cls.get(root, *names)
        except ValueError:
            return []


class AlfaParser(Parser):
    BROKER = 1
    MARKETS = {
        'МБ ФР': 'MB',
        'КЦ МФБ': 'SPB',
        'СПБ': 'SPB',
        'МБ ВР': 'MB',
        'OTC НРД': 'MB',
    }

    @classmethod
    def parse_record(cls, record):
        date = record.attrib['last_update']
        curs = cls.get(record, 'oper_type', 'comment',
                       'money_volume_begin1_Collection',
                       'money_volume_begin1', 'p_code_Collection')
        for cur in curs:
            volume = cls.get(cur, 'p_code').attrib.get('volume')
            if volume:
                cur_code = cls.get(cur, 'p_code').attrib['p_code']
                time = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
                return time, float(volume), cur_code
        raise ValueError('unable to parse')

    def parse(self, content, test=True):
        root = etree.fromstring(content)
        items = []

        # orders section
        collection = chain(self.get(root, 'Trades', 'Report', 'Tablix2',
                                    'Details_Collection'),
                           self.get_silent(root, 'Trades', 'Report', 'Tablix3',
                                           'Details2_Collection'))
        for record in collection:
            isin = (record.attrib.get('isin_reg') or
                    record.attrib.get('isin_reg1')).strip()
            if not isin:
                isin = (record.attrib.get('p_name') or
                        record.attrib.get('p_name2')).strip()
                assert isin in ('EUR', 'USD')

            market = (record.attrib.get('place_name') or
                      record.attrib.get('place_name2')).strip()
            comment = (record.attrib.get('comment') or
                       record.attrib.get('comment2') or '').strip()
            if comment:
                continue
            if market == 'МБ ВР':
                continue

            db_time = (record.attrib.get('db_time') or
                       record.attrib.get('db_time2')).strip()
            qty = (record.attrib.get('qty') or
                   record.attrib.get('qty2')).strip()
            price = (record.attrib.get('Price') or
                     record.attrib.get('Price2')).strip()
            summ_trade = (record.attrib.get('summ_trade') or
                          record.attrib.get('summ_trade2')).strip()
            curr_calc = (record.attrib.get('curr_calc') or
                         record.attrib.get('curr_calc2')).strip()

            data = {
                'date': datetime.strptime(' '.join(db_time.split()[:2]),
                                          '%d.%m.%Y %H:%M:%S'),
                'quantity': int(float(qty)),
                'price': float(price),
                'sum': float(summ_trade),
                'cur': curr_calc,
                'market': self.MARKETS[market],
                'isin': isin,
                **self.portfolio,
            }

            security = SecuritiesManager.get(isin=isin, first=True)
            security_type = security['type']
            if security_type == 'Bond':
                data['price'] = security['faceValue'] * data['price'] / 100
            elif security_type not in ('Stock', 'Etf',):
                raise ValueError(security_type)

            if OrdersManager.get_first(**data) is not None:
                continue

            if test:
                items.append(Order(**data))
            else:
                #OrdersManager.insert(data)
                if 'upserted' in OrdersManager.upsert(data):
                    items.append(Order(**data))

        # money transfer section
        collection = self.get(root, 'Trades2', 'Report', 'Tablix1',
                              'settlement_date_Collection')
        for day in collection:
            for record in self.get(day, 'rn_Collection'):
                time, volume, cur_code = self.parse_record(record)
                oper_type = self.get(record, 'oper_type').attrib[
                    'oper_type'].strip()
                comment = self.get(record, 'oper_type', 'comment').attrib[
                    'comment'].lower()

                if oper_type == 'Перевод':
                    if any(word in comment for word in (
                            'купон', 'dividend', 'дивиденд')):
                        manager = DividendManager
                        model = Dividend
                    elif any(word in comment for word in (
                            'списание по поручению клиента', 'между рынками',
                            'из ао "альфа-банк"')):
                        manager = MoneyManager
                        model = Money
                    else:
                        raise ValueError(comment)
                elif oper_type == 'Комиссия' or oper_type == 'НДФЛ':
                    manager = CommissionManager
                    model = Commission
                    volume = abs(volume)
                else:
                    if oper_type not in ('НКД по сделке', 'Расчеты по сделке'):
                        raise ValueError(oper_type)
                    continue

                data = {
                    'sum': volume,
                    'comment': comment,
                    'cur': cur_code,
                    'date': time,
                    **self.portfolio,
                }
                if test:
                    if manager.get_first(**data) is None:
                        items.append(model(**data))
                else:
                    if 'upserted' in manager.upsert(data):
                        items.append(model(**data))
        return items


class VtbParser(Parser):
    BROKER = 2
    MARKETS = {
        'Фондовый рынок ПАО Московская Биржа': 'MB',
        'ПАО “Санкт-Петербургская Биржа”': 'SPB',
        'Валютный рынок ПАО Московская биржа': 'MB',
    }

    @staticmethod
    def parse_record(record):
        date = record.attrib['debt_type4']
        cur_code = record.attrib['decree_amount2']
        if cur_code == 'RUR':
            cur_code = 'RUB'
        volume = record.attrib.get('debt_date4')
        time = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
        return time, float(volume), cur_code

    def parse(self, content, test=True):
        root = etree.fromstring(content)
        items = []

        # orders section
        collection = self.get(root, 'Tablix_b9', 'Подробности9_Collection')
        for record in collection:
            cur = record.attrib['deal_count7']
            if cur == 'RUR':
                cur = 'RUB'

            quantity = int(float(record.attrib['NameEnd9']))
            if record.attrib['currency_ISO9'] != 'Покупка':
                quantity = -quantity

            isin = record.attrib['NameBeg9'].strip().split(',')[-1].strip()
            data = {
                'market': self.MARKETS[record.attrib['deal_place7']],
                'date': datetime.strptime(record.attrib['curs_datebeg9'],
                                          '%Y-%m-%dT%H:%M:%S'),
                'isin': isin,
                'quantity': quantity,
                'price': float(record.attrib['deal_price7']),
                'sum': float(record.attrib['currency_paym7']),
                'cur': cur,
                **self.portfolio,
            }

            security = SecuritiesManager.get(isin=isin, first=True)
            security_type = security['type']
            if security_type == 'Bond':
                faceValue = security['faceValue']
                data['price'] = faceValue * data['price'] / 100
            elif security_type not in ('Stock', 'Etf',):
                raise ValueError(security_type)

            if OrdersManager.get_first(**data) is not None:
                continue

            if test:
                items.append(Order(**data))
            else:
                if 'upserted' in OrdersManager.upsert(data):
                    items.append(Order(**data))

        # currency orders section
        try:
            collection = self.get(root, 'Tablix_b10',
                                  'Подробности6_Collection')
        except ValueError:
            collection = []
        for record in collection:
            cur = record.attrib['deal_price4']
            if cur == 'RUR':
                cur = 'RUB'

            quantity = int(float(record.attrib['NameEnd6']))
            if record.attrib['currency_ISO6'] != 'Покупка':
                quantity = -quantity

            data = {
                'cur': cur,
                'date': datetime.strptime(record.attrib['curs_datebeg6'],
                                         '%Y-%m-%dT%H:%M:%S'),
                'isin': record.attrib['NameBeg6'].strip()[:3],
                'quantity': quantity,
                'price': float(record.attrib['deal_count4']),
                'sum': float(record.attrib['currency_price4']),
                'market': self.MARKETS[record.attrib['deal_place4']],
                **self.portfolio,
            }
            if OrdersManager.get_first(**data) is not None:
                continue

            if test:
                items.append(Order(**data))
            else:
                if 'upserted' in OrdersManager.upsert(data):
                    items.append(Order(**data))

        # money transfer section
        collection = self.get(root, 'Tablix_b4', 'DDS_place_Collection',
                              'DDS_place', 'Подробности16_Collection')
        for record in collection:
            oper_type = record.attrib['operation_type'].strip()
            comment = record.attrib.get('notes1', '').lower()

            time, volume, cur_code = self.parse_record(record)
            if (oper_type == 'Зачисление денежных средств' or
                    oper_type == 'Дивиденды'):
                if any(word in comment for word in ('купон', 'dividend',
                                                    'дивиденд')):
                    manager = DividendManager
                    model = Dividend
                elif not comment or 'перечисление денежных средств' in comment:
                    manager = MoneyManager
                    model = Money
                else:
                    raise ValueError(comment)
            elif oper_type == 'Вознаграждение Брокера':
                manager = CommissionManager
                model = Commission
                volume = abs(volume)
            else:
                if oper_type not in (
                        'Сальдо расчётов по сделкам с ценными бумагами',
                        'Сальдо расчётов по сделкам с иностранной валютой'):
                    raise ValueError(oper_type)
                continue

            data = {
                'sum': volume,
                'comment': comment,
                'cur': cur_code,
                'date': time,
                **self.portfolio,
            }

            if test:
                if manager.get_first(**data) is None:
                    items.append(model(**data))
            else:
                if 'upserted' in manager.upsert(data):
                    item = model(**data)
                    items.append(item)
        return items


PARSERS = {
    Portfolio.ALFA: AlfaParser,
    Portfolio.VTB: VtbParser,
}


def parse(content, broker, test=True):
    parser = PARSERS[broker](1)
    return parser.parse(content, test=test)
