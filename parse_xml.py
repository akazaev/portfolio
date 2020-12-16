from datetime import datetime

import xml.etree.ElementTree as etree

from managers import DividendManager, CommissionManager


tree = etree.parse('reports/report.xml')
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
    date = record.attrib['last_update']
    curs = get(record, 'oper_type', 'comment',
               'money_volume_begin1_Collection',
               'money_volume_begin1', 'p_code_Collection')
    for cur in curs:
        volume = get(cur, 'p_code').attrib.get('volume')
        if volume:
            cur_code = get(cur, 'p_code').attrib['p_code']
            print(volume, cur_code, comment)
            time = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
            return time, abs(float(volume)), cur_code
    raise ValueError('unable to parse')


types = set()
collection = get(root, 'Trades2', 'Report', 'Tablix1',
                 'settlement_date_Collection')
for day in collection:
    for record in get(day, 'rn_Collection'):
        oper_type = get(record, 'oper_type').attrib['oper_type'].strip()
        comment = get(record, 'oper_type', 'comment').attrib['comment'].lower()
        if oper_type == 'Перевод':
            if any(word in comment
                   for word in ('купон', 'dividend', 'дивиденд')):
                time, volume, cur_code = parse_record(record)
                data = {
                        'portfolio': 1,
                        'sum': volume,
                        'broker': 1,
                        'comment': comment,
                        'cur': cur_code,
                        'date': time
                }
                DividendManager.upsert(data)
        elif oper_type == 'Комиссия':
            time, volume, cur_code = parse_record(record)
            data = {
                'portfolio': 1,
                'sum': volume,
                'broker': 1,
                'comment': comment,
                'cur': cur_code,
                'date': time
            }
            CommissionManager.upsert(data)
        else:
            types.add(oper_type)

print(types)
