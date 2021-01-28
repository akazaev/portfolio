from datetime import datetime

import xml.etree.ElementTree as etree

from portfolio.managers import (
    DividendManager, CommissionManager, MoneyManager)


tree = etree.parse('GetBrokerReport.xml')
root = tree.getroot()


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


def parse_record(record):
    date = record.attrib['debt_type4']
    cur_code = record.attrib['decree_amount2']
    if cur_code == 'RUR':
        cur_code = 'RUB'
    volume = record.attrib.get('debt_date4')
    time = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
    return time, float(volume), cur_code


types = set()
collection = get(root, 'Tablix_b4', 'DDS_place_Collection', 'DDS_place',
                 'Подробности16_Collection')

for record in collection:
    oper_type = record.attrib['operation_type'].strip()
    comment = record.attrib.get('notes1', '').lower()

    if oper_type == 'Зачисление денежных средств':
        if any(word in comment for word in ('купон', 'dividend', 'дивиденд')):
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
    else:
        types.add(oper_type)

print(types)
