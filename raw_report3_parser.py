import datetime
from collections import namedtuple

from examples.mongo import insert, clear


class States:
    STOCK = 1
    STOCK_TABLE = 2
    STOCK_HEADER = 3


OPERATIONS = {
    'Комиссия': 'commission',
    'Перевод': 'transfer',
    'НДФЛ': 'tax',
    'Расчеты по сделке': 'payment',
    'НКД по сделке': 'payment',
}


def parse_line(market, line, cur_date):
    operation = line[4]
    assert operation in OPERATIONS
    assert market in ('s', 'c', )
    operation = OPERATIONS[operation]
    comment = line[5]

    if operation == 'transfer':
        if 'dividend' in comment.lower() or 'дивиденд' in comment.lower():
            operation = 'dividend'
        elif 'из ао' in comment.lower():
            operation = 'transfer_in'
        elif 'списание' in comment.lower():
            operation = 'transfer_out'
        elif 'между' in comment.lower():
            operation = 'transfer'
        else:
            raise NotImplemented

    date = datetime.datetime.strptime(line[1], '%d.%m.%Y %H:%M:%S')

    rub = line[10].replace(' ', '').replace('- ', '-').replace(',', '.')
    rub = float(rub or '0')
    usd = line[16].replace(' ', '').replace('- ', '-').replace(',', '.')
    usd = float(usd or '0')
    eur = line[20].replace(' ', '').replace('- ', '-').replace(',', '.')
    eur = float(eur or '0')

    row = Row(market=market, date=date, operation=operation, comment=comment,
              rub=rub, usd=usd, eur=eur)
    return row, line[0] or cur_date


raw = []
with open('reports/raw_report3.csv') as f:
    s = f.readline()
    while s:
        raw.append(s.split(';'))
        s = f.readline()


Row = namedtuple('Row', ['market', 'date', 'operation', 'comment', 'rub',
                         'usd', 'eur'])

market = None
report = []
state = None
cur_date = None
for line in raw:
    line = [col.rstrip('"').lstrip('"') for col in line]
    if line[0] == 'Фондовый рынок' and state is None:
        market = 's'
        state = States.STOCK
    elif line[0] == 'Валютный рынок' and state is None:
        market = 'c'
        state = States.STOCK
    elif state == States.STOCK and line[0] == 'Дата':
        state = States.STOCK_HEADER
    elif state == States.STOCK_HEADER and not line[0]:
        state = States.STOCK_HEADER
    elif state == States.STOCK_HEADER and line[0]:
        state = States.STOCK_TABLE
        parsed = parse_line(market, line, cur_date)
        if parsed:
            row, cur_date = parsed
            report.append(row)
    elif state == States.STOCK_TABLE and (line[0] or line[1]):
        parsed = parse_line(market, line, cur_date)
        if parsed:
            row, cur_date = parsed
            report.append(row)
    elif state == States.STOCK_TABLE and not (line[0] or line[1]):
        state = None


money_save = []

with open('reports/report3.csv', 'w') as f:
    f.write(';'.join(Row._fields) + '\n')
    report.sort(key=lambda x: x.date)
    for row in report:
        line = ';'.join(str(getattr(row, field))
                        for field in Row._fields) + '\n'
        f.write(line)

        if row.market != 's' or 'transfer' not in row.operation:
            continue

        if row.rub:
            sum = row.rub
            cur = 'RUB'
        elif row.eur:
            sum = row.eur
            cur = 'EUR'
        elif row.usd:
            sum = row.usd
            cur = 'USD'
        else:
            raise NotImplemented()

        money_save.append({
            'portfolio': 1,
            'date': row.date,
            'sum': sum,
            'cur': cur,
            'comment': row.comment})


clear('money')
insert('money', money_save)
