import datetime
from collections import namedtuple

from examples.mongo import insert, clear


class States:
    STOCK = 1
    STOCK_TABLE =2
    STOCK_HEADER = 3


MARKETS = {
    'МБ ФР': 'MB',
    'КЦ МФБ': 'SPB',
    'СПБ': 'SPB',
    'МБ ВР': 'MBV',
    'OTC НРД': 'MB',
}


def parse_line(line):
    date1 = line[0].rstrip('"').lstrip('"').replace('  ', ' ')
    date1 = datetime.datetime.strptime(date1, '%d.%m.%Y %H:%M:%S')
    date2 = line[1].rstrip('"').lstrip('"').replace('  ', ' ')
    #date2 = datetime.datetime.strptime(date2, '%d.%m.%Y %H:%M:%S')
    date2 = None

    market = line[5].rstrip('"').lstrip('"').replace('  ', ' ')
    assert market in MARKETS
    market = MARKETS[market]

    isin = line[6].rstrip('"').lstrip('"').replace('  ', ' ')
    if not isin:
        isin = line[9].rstrip('"').lstrip('"').replace('  ', ' ')

    price = line[17].replace(',', '.')
    sum = line[18].replace(',', '.')
    cur = line[22].rstrip('"').lstrip('"')

    row = Row(date1=date1, date2=date2, market=market, isin=isin,
              quantity=int(line[14]), price=float(price), sum=float(sum),
              cur=cur, comission=line[23])
    return row


content = ''
quotes = False
changed = False
with open('reports/raw_report2.csv') as f:
    while True:
        s = f.read(1)
        if not s:
            break
        if s == '"':
            quotes = not quotes
        
        if s == '\n' and quotes:
            content += ' '
            changed = True
        else:
            content += s


if changed:
    with open('reports/raw_report2.csv', 'w') as f:
        f.write(content)


raw = []
with open('reports/raw_report2.csv') as f:
    s = f.readline()
    while s:
        raw.append(s.split(';'))
        s = f.readline()


Row = namedtuple('Row', ['date1', 'date2', 'market', 'isin', 'quantity',
                         'price', 'sum', 'cur', 'comission'])

orders_save = []
report = []
state = None
for line in raw:
    line = line[1:]
    #if 'Незавершенные' in line[0]:
    #    break

    if 'Дата заключен' in line[0] and state is None:
        state = States.STOCK
    elif state == States.STOCK and not (line[0] or line[1]):
        state = None
    elif state == States.STOCK:
        if line[24].strip():
            continue  # skip repo and swap
        line = parse_line(line)
        report.append(line)

        if line.date1 < datetime.datetime(2020, 11, 13):
            continue

        if line.market != 'MBV':
            orders_save.append({
                'portfolio': 1,
                'date': line.date1,
                'market': line.market,
                'isin': line.isin,
                'quantity': line.quantity,
                'price': line.price,
                'sum': line.sum,
                'cur': line.cur,
                'broker': 1})


import pprint
pprint.pprint(orders_save)
#clear('orders')
insert('orders', orders_save)


with open('reports/report2.csv', 'w') as f:
    f.write(';'.join(Row._fields) + '\n')
    report.sort(key=lambda x: x.date1)
    for row in report:
        line = ';'.join(str(getattr(row, field))
                        for field in Row._fields) + '\n'
        f.write(line)
