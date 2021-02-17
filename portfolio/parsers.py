from datetime import datetime

import xml.etree.ElementTree as etree

from portfolio.managers import (
    Order, Dividend, DividendManager, Commission, CommissionManager,
    Money, MoneyManager, OrdersManager, SecuritiesManager)
from portfolio.portfolio import Portfolio


def get_child(root, child_tag):
    for child in root:
        if child_tag in child.tag:
            return child
    raise ValueError('not found')


def get(root, *names):
    if len(names) == 1:
        names = names[0]
        names = names.split('.')
    for name in names:
        root = get_child(root, name)
        if root is None:
            raise ValueError('not found')
    return root


ALFA_MARKETS = {
    'МБ ФР': 'MB',
    'КЦ МФБ': 'SPB',
    'СПБ': 'SPB',
    'МБ ВР': 'MB',
    'OTC НРД': 'MB',
}


VTB_MARKETS = {
    'Фондовый рынок ПАО Московская Биржа': 'MB',
    'ПАО “Санкт-Петербургская Биржа”': 'SPB',
    'Валютный рынок ПАО Московская биржа': 'MB',
}


def parse_alfa_report(content, broker_id=1, test=True):
    def parse_record(record):
        date = record.attrib['last_update']
        curs = get(record, 'oper_type', 'comment',
                   'money_volume_begin1_Collection',
                   'money_volume_begin1', 'p_code_Collection')
        for cur in curs:
            volume = get(cur, 'p_code').attrib.get('volume')
            if volume:
                cur_code = get(cur, 'p_code').attrib['p_code']
                time = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
                return time, float(volume), cur_code
        raise ValueError('unable to parse')

    root = etree.fromstring(content)

    # orders section
    collection = get(root, 'Trades', 'Report', 'Tablix2', 'Details_Collection')
    orders = []

    for record in collection:
        date = datetime.strptime(
            ' '.join(record.attrib['db_time'].strip().split()[:2]),
            '%d.%m.%Y %H:%M:%S')
        isin = record.attrib['isin_reg'].strip()
        if not isin:
            isin = record.attrib['p_name'].strip()
            assert isin in ('EUR', 'USD')

        market = record.attrib['place_name']
        comment = record.attrib.get('comment')
        if comment:
            continue
        if market == 'МБ ВР':
            continue

        quantity = int(float(record.attrib['qty']))
        price = float(record.attrib['Price'])
        sum = float(record.attrib['summ_trade'])
        cur = record.attrib['curr_calc']
        market = ALFA_MARKETS[market]

        result = OrdersManager.get(date=date, isin=isin,
                                   quantity=quantity,
                                   sum=sum, cur=cur, market=market,
                                   portfolio=1, broker=broker_id,
                                   first=True)

        if result is None:
            security = SecuritiesManager.get(isin=isin, first=True)
            security_type = security['type']
            if security_type in ('Stock', 'Etf'):
                data = dict(portfolio=1, broker=broker_id,
                            sum=sum, cur=cur,
                            date=date, market=market, isin=isin,
                            quantity=quantity, price=price)
            elif security_type == 'Bond':
                faceValue = security['faceValue']
                data = dict(portfolio=1, broker=broker_id,
                            sum=sum, cur=cur,
                            date=date, market=market, isin=isin,
                            quantity=quantity,
                            price=faceValue * price / 100)
            else:
                raise ValueError(security_type)

            if not test:
                #OrdersManager.insert(data)
                result = OrdersManager.upsert(data)
            if test and not result or 'upserted' in result:
                item = Order(**data)
                orders.append(item)

    # money transfer section
    collection = get(root, 'Trades2', 'Report', 'Tablix1',
                     'settlement_date_Collection')
    money = []
    dividend = []
    commission = []

    for day in collection:
        for record in get(day, 'rn_Collection'):
            oper_type = get(record, 'oper_type').attrib['oper_type'].strip()
            comment = get(record, 'oper_type', 'comment').attrib[
                'comment'].lower()

            if oper_type == 'Перевод':
                if any(word in comment for word in (
                        'купон', 'dividend', 'дивиденд')):
                    time, volume, cur_code = parse_record(record)
                    data = {
                        'portfolio': 1,
                        'sum': volume,
                        'broker': 1,
                        'comment': comment,
                        'cur': cur_code,
                        'date': time
                    }
                    if test:
                        result = DividendManager.get(**data, first=True)
                    else:
                        result = DividendManager.upsert(data)
                    if test and not result or 'upserted' in result:
                        print(data)
                        item = Dividend(date=time, cur=cur_code, sum=volume,
                                        portfolio=1, broker=broker_id,
                                        comment=comment)
                        dividend.append(item)
                elif any(word in comment for word in (
                        'списание по поручению клиента', 'между рынками',
                        'из ао "альфа-банк"')):
                    time, volume, cur_code = parse_record(record)
                    data = {
                        'portfolio': 1,
                        'sum': volume,
                        'broker': 1,
                        'comment': comment,
                        'cur': cur_code,
                        'date': time
                    }
                    if test:
                        result = MoneyManager.get(**data, first=True)
                    else:
                        result = MoneyManager.upsert(data)
                    if test and not result or 'upserted' in result:
                        print(data)
                        item = Money(date=time, cur=cur_code, sum=volume,
                                     portfolio=1, broker=broker_id,
                                     comment=comment)
                        money.append(item)
                else:
                    raise ValueError(comment)
            elif oper_type == 'Комиссия' or oper_type == 'НДФЛ':
                time, volume, cur_code = parse_record(record)
                data = {
                    'portfolio': 1,
                    'sum': abs(volume),
                    'broker': 1,
                    'comment': comment,
                    'cur': cur_code,
                    'date': time
                }
                if test:
                    result = CommissionManager.get(**data, first=True)
                else:
                    result = CommissionManager.upsert(data)
                if test and not result or 'upserted' in result:
                    print(data)
                    item = Commission(date=time, cur=cur_code, sum=abs(volume),
                                      comment=comment, portfolio=1,
                                      broker=broker_id)
                    commission.append(item)
            else:
                if oper_type not in ('НКД по сделке', 'Расчеты по сделке'):
                    raise ValueError(oper_type)
    return orders, money, dividend, commission


def parse_vtb_report(content, broker_id=2, test=True):
    def parse_record(record):
        date = record.attrib['debt_type4']
        cur_code = record.attrib['decree_amount2']
        if cur_code == 'RUR':
            cur_code = 'RUB'
        volume = record.attrib.get('debt_date4')
        time = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
        return time, float(volume), cur_code

    root = etree.fromstring(content)

    # orders section
    orders = []
    collection = get(root, 'Tablix_b9', 'Подробности9_Collection')

    for record in collection:
        date = datetime.strptime(record.attrib['curs_datebeg9'],
                                 '%Y-%m-%dT%H:%M:%S')
        isin = record.attrib['NameBeg9'].strip().split(',')[-1].strip()
        quantity = int(float(record.attrib['NameEnd9']))
        price = float(record.attrib['deal_price7'])
        sum = float(record.attrib['currency_paym7'])
        cur = record.attrib['deal_count7']
        if cur == 'RUR':
            cur = 'RUB'
        market = VTB_MARKETS[record.attrib['deal_place7']]

        if record.attrib['currency_ISO9'] != 'Покупка':
            quantity = -quantity

        result = OrdersManager.get(date=date, isin=isin,
                                   quantity=quantity,
                                   sum=sum, cur=cur, market=market,
                                   portfolio=1, broker=2,
                                   first=True)
        if result is None:
            security = SecuritiesManager.get(isin=isin, first=True)
            security_type = security['type']
            if security_type in ('Stock', 'Etf'):
                data = dict(portfolio=1, broker=2,
                            sum=sum, cur=cur,
                            date=date, market=market, isin=isin,
                            quantity=quantity, price=price)
            elif security_type == 'Bond':
                faceValue = security['faceValue']
                data = dict(portfolio=1, broker=2,
                            sum=sum, cur=cur,
                            date=date, market=market, isin=isin,
                            quantity=quantity,
                            price=faceValue * price / 100)
            else:
                raise ValueError(security_type)
            if not test:
                result = OrdersManager.upsert(data)
            if test and not result or 'upserted' in result:
                item = Order(**data)
                orders.append(item)

    collection = get(root, 'Tablix_b10', 'Подробности6_Collection')

    for record in collection:
        date = datetime.strptime(record.attrib['curs_datebeg6'],
                                 '%Y-%m-%dT%H:%M:%S')
        isin = record.attrib['NameBeg6'].strip()[:3]
        quantity = int(float(record.attrib['NameEnd6']))
        price = float(record.attrib['deal_count4'])
        sum = float(record.attrib['currency_price4'])
        cur = record.attrib['deal_price4']
        if cur == 'RUR':
            cur = 'RUB'
        market = VTB_MARKETS[record.attrib['deal_place4']]

        result = OrdersManager.get(date=date, isin=isin,
                                   quantity=quantity,
                                   sum=sum, cur=cur, market=market,
                                   portfolio=1, broker=2,
                                   first=True)

        if result is None:
            data = dict(portfolio=1, broker=2,
                        sum=sum, cur=cur,
                        date=date, market=market, isin=isin,
                        quantity=quantity, price=price)
            if not test:
                result = OrdersManager.upsert(data)
            if test and not result or 'upserted' in result:
                item = Order(**data)
                orders.append(item)

    # money transfer section
    collection = get(root, 'Tablix_b4', 'DDS_place_Collection', 'DDS_place',
                     'Подробности16_Collection')
    money = []
    dividend = []
    commission = []

    for record in collection:
        oper_type = record.attrib['operation_type'].strip()
        comment = record.attrib.get('notes1', '').lower()

        if oper_type == 'Зачисление денежных средств':
            if any(word in comment for word in ('купон', 'dividend',
                                                'дивиденд')):
                time, volume, cur_code = parse_record(record)
                data = {
                        'portfolio': 1,
                        'sum': volume,
                        'broker': 2,
                        'comment': comment,
                        'cur': cur_code,
                        'date': time
                }
                if test:
                    result = DividendManager.get(**data, first=True)
                else:
                    result = DividendManager.upsert(data)
                if test and not result or 'upserted' in result:
                    print(data)
                    item = Dividend(date=time, cur=cur_code, sum=volume,
                                    portfolio=1, broker=broker_id,
                                    comment=comment)
                    dividend.append(item)
            elif not comment or 'перечисление денежных средств' in comment:
                time, volume, cur_code = parse_record(record)
                data = {
                        'portfolio': 1,
                        'sum': volume,
                        'broker': 2,
                        'comment': comment,
                        'cur': cur_code,
                        'date': time
                }
                if test:
                    result = MoneyManager.get(**data, first=True)
                else:
                    result = MoneyManager.upsert(data)
                if test and not result or 'upserted' in result:
                    print(data)
                    item = Money(date=time, cur=cur_code, sum=volume,
                                 portfolio=1, broker=broker_id,
                                 comment=comment)
                    money.append(item)
            else:
                raise ValueError(comment)
        elif oper_type == 'Вознаграждение Брокера':
            time, volume, cur_code = parse_record(record)
            data = {
                'portfolio': 1,
                'sum': abs(volume),
                'broker': 2,
                'comment': comment,
                'cur': cur_code,
                'date': time
            }
            if test:
                result = CommissionManager.get(**data, first=True)
            else:
                result = CommissionManager.upsert(data)
            if test and not result or 'upserted' in result:
                print(data)
                item = Commission(date=time, cur=cur_code, sum=abs(volume),
                                  comment=comment, portfolio=1,
                                  broker=broker_id)
                commission.append(item)
        else:
            if oper_type not in (
                    'Сальдо расчётов по сделкам с ценными бумагами',
                    'Сальдо расчётов по сделкам с иностранной валютой'):
                raise ValueError(oper_type)
    return orders, money, dividend, commission


PARSERS = {
    Portfolio.ALFA: parse_alfa_report,
    Portfolio.VTB: parse_vtb_report,
}


def parse(content, broker, test=True):
    parser = PARSERS[broker]
    return parser(content, test=test)
