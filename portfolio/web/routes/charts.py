from datetime import datetime, timedelta
import json

from flask import Blueprint, templating, request
import plotly

from portfolio.portfolio import Portfolio,  TimeRange

charts = Blueprint('charts', __name__, url_prefix='/charts')


RANGE_LAYOUT = {
    'autosize': False,
    'width': 1900,
    'height': 900,
    'title': 'first graph',
    'xaxis': dict(
        rangeselector=dict(
            buttons=list([
                dict(count=1,
                     label="1m",
                     step="month",
                     stepmode="backward"),
                dict(count=6,
                     label="6m",
                     step="month",
                     stepmode="backward"),
                dict(count=1,
                     label="YTD",
                     step="year",
                     stepmode="todate"),
                dict(count=1,
                     label="1y",
                     step="year",
                     stepmode="backward"),
                dict(step="all")
            ])
        ),
        rangeslider=dict(
            visible=True
        ),
        type="date"
    )
}


@charts.route('/value')
def value_chart():
    portfolio = Portfolio(1)
    start_date = None
    end_date = datetime.now() - timedelta(days=1)
    time_range = TimeRange(start_date, end_date)
    cur = request.args.get('cur', Portfolio.RUB)

    data = portfolio.get_value_history(time_range, currency=cur)
    cbr_data = portfolio.get_cbr_history(time_range, currency=cur)
    cash_data = portfolio.get_cash_history(time_range, currency=cur)
    dividend_data = portfolio.get_dividend_history(time_range, currency=cur)
    samples = [dividend_data + data, cbr_data, cash_data]

    data = {
        'data': [],
        'layout': RANGE_LAYOUT
    }

    for sample in samples:
        data['data'].append({
            'x': list(sample.keys()),
            'y': list(sample.values()),
            'name': sample.title,
        })

    data = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
    return templating.render_template('chart.html', data=data)


@charts.route('/profit')
def profit_chart():
    portfolio = Portfolio(1)
    start_date = None
    end_date = datetime.now() - timedelta(days=1)
    time_range = TimeRange(start_date, end_date)
    cur = request.args.get('cur', Portfolio.RUB)

    data = portfolio.get_value_history(time_range, currency=cur)
    cbr_data = portfolio.get_cbr_history(time_range, currency=cur)
    cash_data = portfolio.get_cash_history(time_range, currency=cur)
    dividend_data = portfolio.get_dividend_history(time_range, currency=cur)
    commission_data = portfolio.get_commission_history(time_range,
                                                       currency=cur)
    samples = [data - cash_data, cbr_data - cash_data, dividend_data,
               commission_data]

    data = {
        'data': [],
        'layout': RANGE_LAYOUT
    }

    for sample in samples:
        data['data'].append({
            'x': list(sample.keys()),
            'y': list(sample.values()),
            'name': sample.title,
        })

    data = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
    return templating.render_template('chart.html', data=data)


@charts.route('/profit_percent')
def profit_percent_chart():
    portfolio = Portfolio(1)
    start_date = None
    end_date = datetime.now() - timedelta(days=1)
    time_range = TimeRange(start_date, end_date)
    cur = request.args.get('cur', Portfolio.RUB)

    data = portfolio.get_value_history(time_range, currency=cur)
    cbr_data = portfolio.get_cbr_history(time_range, currency=cur)
    cash_data = portfolio.get_cash_history(time_range, currency=cur)
    dividend_data = portfolio.get_dividend_history(time_range, currency=cur)
    samples = [100 * (data - cash_data) / cash_data,
               100 * (data + dividend_data - cash_data) / cash_data,
               100 * (cbr_data - cash_data) / cash_data]

    data = {
        'data': [],
        'layout': RANGE_LAYOUT
    }

    for sample in samples:
        data['data'].append({
            'x': list(sample.keys()),
            'y': list(sample.values()),
            'name': sample.title,
        })

    data = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
    return templating.render_template('chart.html', data=data)


@charts.route('/portfolio')
def portfolio_chart():
    portfolio = Portfolio(portfolio_id=1)
    state_asset, state_cur = portfolio.get_state(total=False)
    values = []
    labels = []
    for item in state_asset:
        ticker, name, quantity, sec_cur, position_orig, position = item
        values.append(position)
        labels.append(name)

    data = {
        'data': [
            {
                'values': values,
                'labels': labels,
                'type': 'pie'
            }
        ],
        'layout': {
            'autosize': False,
            'width': 1900,
            'height': 900,
        }
    }

    data = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
    return templating.render_template('chart.html', data=data)
