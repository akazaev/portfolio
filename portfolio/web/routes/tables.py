from flask import Blueprint, templating
from flask_table import Table, Col

from portfolio.managers import MoneyManager, OrdersManager
from portfolio.portfolio import Portfolio

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


class PortfolioTable(Table):
    ticker = Col('Ticker')
    name = Col('Name')
    quantity = Col('Quantity')
    sec_cur = Col('Cur')
    position_orig = Col('Sum')
    position = Col('Sum (RUB)')


@tables.route('/portfolio')
def portfolio_table():
    portfolio = Portfolio(portfolio_id=1)
    data = portfolio.get_state()
    items = []
    for item in data:
        ticker, name, quantity, sec_cur, position_orig, position = item
        items.append({
            'ticker': ticker,
            'name': name,
            'quantity': quantity,
            'sec_cur': sec_cur,
            'position_orig': position_orig,
            'position': position
        })
    table = PortfolioTable(items, classes=['table', 'table-dark'])
    return templating.render_template('table.html', table=table)
