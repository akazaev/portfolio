import datetime

from flask import Blueprint, templating, redirect, request
from flask_wtf import FlaskForm, file
from wtforms import (
    StringField, FloatField, IntegerField, SelectField, HiddenField)
from wtforms.validators import DataRequired
from wtforms.fields.html5 import DateField


from portfolio.portfolio import Portfolio
from portfolio.managers import OrdersManager, MoneyManager, DividendManager
from portfolio.parsers import parse
from portfolio.web.routes.tables import (
    OrdersTable, MoneyTable, DividendsTable, CommissionTable)


forms = Blueprint('forms', __name__, url_prefix='/forms')


class CustomDateField(DateField):
    def process_formdata(self, valuelist):
        if valuelist:
            date_str = ' '.join(valuelist)
            try:
                self.data = datetime.datetime.strptime(date_str, self.format)
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid date value'))


class BaseForm(FlaskForm):
    portfolio = IntegerField('Portfolio', validators=[DataRequired()])
    broker = IntegerField('Broker', validators=[DataRequired()])
    sum = FloatField('Sum', validators=[DataRequired()])
    cur = SelectField('Cur', validators=[DataRequired()],
                      choices=(
                          (Portfolio.RUB, Portfolio.RUB),
                          (Portfolio.USD, Portfolio.USD),
                          (Portfolio.EUR, Portfolio.EUR),
                      ))
    date = CustomDateField('Date', validators=[DataRequired()])


class OrderForm(BaseForm):
    market = SelectField('Market', validators=[DataRequired()],
                         choices=(
                             (Portfolio.MB, Portfolio.MB),
                             (Portfolio.SPB, Portfolio.SPB),
                         ))
    isin = StringField('ISIN', validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])


@forms.route('/order', methods=('GET', 'POST'))
def order_submit():
    form = OrderForm()
    if form.validate_on_submit():
        data = form.data
        data.pop('csrf_token', None)
        OrdersManager.insert(data)
        return redirect('/tables/orders')
    return templating.render_template('form.html', form=form)


class MoneyForm(BaseForm):
    comment = StringField('Comment', validators=[DataRequired()])


@forms.route('/money', methods=('GET', 'POST'))
def money_submit():
    form = MoneyForm()
    if form.validate_on_submit():
        data = form.data
        data.pop('csrf_token', None)
        MoneyManager.insert(data)
        return redirect('/tables/money')
    return templating.render_template('form.html', form=form)


class DividendForm(BaseForm):
    comment = StringField('Comment', validators=[DataRequired()])


@forms.route('/dividend', methods=('GET', 'POST'))
def dividend_submit():
    form = DividendForm()
    if form.validate_on_submit():
        data = form.data
        data.pop('csrf_token', None)
        DividendManager.insert(data)
        return redirect('/tables/dividends')
    return templating.render_template('form.html', form=form)


class ReportForm(FlaskForm):
    broker = SelectField('Market', validators=[DataRequired()],
                         choices=(
                             (Portfolio.ALFA, Portfolio.ALFA),
                             (Portfolio.VTB, Portfolio.VTB),
                         ))
    report = file.FileField(validators=[file.FileRequired()])
    test = HiddenField('test')


@forms.route('/report', methods=('GET', 'POST'))
def load_report():
    form = ReportForm()
    if form.validate_on_submit():
        content = request.files['report'].read()
        broker = form.data['broker']
        test = bool(form.data['test'])
        orders, money, dividend, commission = parse(content, broker, test=test)

        tables = [
            OrdersTable(orders, classes=['table', 'table-dark']),
            MoneyTable(money, classes=['table', 'table-dark']),
            DividendsTable(dividend, classes=['table', 'table-dark']),
            CommissionTable(commission, classes=['table', 'table-dark'])
        ]
        return templating.render_template('tables.html', tables=tables)
    return templating.render_template('form.html', form=form)
