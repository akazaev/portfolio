from flask import Blueprint, templating, request
from flask_table import Table, Col

from portfolio.managers import MoneyManager, OrdersManager, DividendManager
from portfolio.portfolio import Portfolio

tables = Blueprint('tables', __name__, url_prefix='/tables')


class BaseTable(Table):
    date = Col('Date')
    sum = Col('Sum')
    cur = Col('Cur')
    broker = Col('Broker')


class MoneyTable(BaseTable):
    title = 'Money'


@tables.route('/money')
def money_table():
    broker = request.args.get('broker')
    items = MoneyManager.get_data(broker_id=int(broker) if broker else None,
                                  sort=-1)
    table = MoneyTable(items, classes=['table', 'table-dark'])
    return templating.render_template('table.html', table=table)


class OrdersTable(BaseTable):
    title = 'Orders'
    isin = Col('ISIN')
    quantity = Col('quantity')


@tables.route('/orders')
def orders_table():
    broker = request.args.get('broker')
    items = OrdersManager.get_data(broker_id=int(broker) if broker else None,
                                   sort=-1)
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
    broker = request.args.get('broker')
    portfolio = Portfolio(broker_id=int(broker) if broker else None,
                          portfolio_id=1)
    state_asset, state_cur = portfolio.get_state()
    items = []
    for item in state_asset:
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


class DividendsTable(BaseTable):
    title = 'Dividends'


class CommissionTable(BaseTable):
    title = 'Commission'


@tables.route('/dividends')
def dividends_table():
    broker = request.args.get('broker')
    items = DividendManager.get_data(broker_id=int(broker) if broker else None,
                                     sort=-1)
    table = DividendsTable(items, classes=['table', 'table-dark'])
    return templating.render_template('table.html', table=table)
