import datetime

from flask import Blueprint, templating, redirect
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, IntegerField
from wtforms.validators import DataRequired
from wtforms.fields.html5 import DateField


from portfolio.managers import OrdersManager


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


class OrderForm(FlaskForm):
    portfolio = IntegerField('Portfolio', validators=[DataRequired()])
    broker = IntegerField('Broker', validators=[DataRequired()])
    sum = FloatField('Sum', validators=[DataRequired()])
    cur = StringField('Cur', validators=[DataRequired()])
    date = CustomDateField('Date', validators=[DataRequired()])
    market = StringField('Market', validators=[DataRequired()])
    isin = StringField('ISIN', validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])


@forms.route('/order', methods=('GET', 'POST'))
def submit():
    form = OrderForm()
    if form.validate_on_submit():
        data = form.data
        data.pop('csrf_token', None)
        OrdersManager.insert(data)
        return redirect('/tables/orders')
    return templating.render_template('form.html', form=form)
