from flask import Blueprint, templating
from flask_table import Table, Col

from portfolio.managers import MoneyManager, OrdersManager

tables = Blueprint('tables', __name__, url_prefix='/tables')


class MoneyTable(Table):
    date = Col('Date')
    sum = Col('Sum')
    cur = Col('Cur')
    broker = Col('Broker')


@tables.route('/money')
def money_table():
    items = MoneyManager.get_data()
    table = MoneyTable(items, classes=['table', 'table-dark'])
    return templating.render_template('table.html', table=table)


class OrdersTable(Table):
    date = Col('Date')
    sum = Col('Sum')
    cur = Col('Cur')
    broker = Col('Broker')
    isin = Col('ISIN')
    quantity = Col('quantity')


@tables.route('/orders')
def orders_table():
    items = OrdersManager.get_data(sort=-1)
    table = OrdersTable(items, classes=['table', 'table-dark'])
    return templating.render_template('table.html', table=table)
