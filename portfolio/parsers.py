from datetime import datetime

import xml.etree.ElementTree as etree

from portfolio.managers import (
    Dividend, DividendManager, Commission, CommissionManager,
    Money, MoneyManager)
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


def parse_alfa_report(content):
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
    collection = get(root, 'Trades2', 'Report', 'Tablix1',
                     'settlement_date_Collection')
    upserted = []

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
                    result = DividendManager.upsert(data)
                    if 'upserted' in result:
                        print(data)
                        item = Dividend(date=time, cur=cur_code, sum=volume,
                                        portfolio=1, broker=1, comment=comment)
                        upserted.append(item)
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
                    result = MoneyManager.upsert(data)
                    if 'upserted' in result:
                        print(data)
                        item = Money(date=time, cur=cur_code, sum=volume,
                                     portfolio=1, broker=1, comment=comment)
                        upserted.append(item)
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
                result = CommissionManager.upsert(data)
                if 'upserted' in result:
                    print(data)
                    item = Commission(date=time, cur=cur_code, sum=abs(volume),
                                      comment=comment, portfolio=1, broker=1)
                    upserted.append(item)
            else:
                if oper_type not in ('НКД по сделке', 'Расчеты по сделке'):
                    raise ValueError(oper_type)
    return upserted


def parse_vtb_report(content):
    def parse_record(record):
        date = record.attrib['debt_type4']
        cur_code = record.attrib['decree_amount2']
        if cur_code == 'RUR':
            cur_code = 'RUB'
        volume = record.attrib.get('debt_date4')
        time = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
        return time, float(volume), cur_code

    root = etree.fromstring(content)
    collection = get(root, 'Tablix_b4', 'DDS_place_Collection', 'DDS_place',
                     'Подробности16_Collection')
    upserted = []

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
                result = DividendManager.upsert(data)
                if 'upserted' in result:
                    print(data)
                    item = Dividend(date=time, cur=cur_code, sum=volume,
                                    portfolio=1, broker=2, comment=comment)
                    upserted.append(item)
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
                result = MoneyManager.upsert(data)
                if 'upserted' in result:
                    print(data)
                    item = Money(date=time, cur=cur_code, sum=volume,
                                 portfolio=1, broker=2, comment=comment)
                    upserted.append(item)
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
            result = CommissionManager.upsert(data)
            if 'upserted' in result:
                print(data)
                item = Commission(date=time, cur=cur_code, sum=abs(volume),
                                  comment=comment, portfolio=1, broker=2)
                upserted.append(item)
        else:
            if oper_type not in (
                    'Сальдо расчётов по сделкам с ценными бумагами',
                    'Сальдо расчётов по сделкам с иностранной валютой'):
                raise ValueError(oper_type)
    return upserted


PARSERS = {
    Portfolio.ALFA: parse_alfa_report,
    Portfolio.VTB: parse_vtb_report,
}


def parse(content, broker):
    parser = PARSERS[broker]
    return parser(content)
