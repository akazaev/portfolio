from flask import Blueprint, templating, redirect
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, IntegerField
from wtforms.validators import DataRequired
from wtforms.fields.html5 import DateField


forms = Blueprint('forms', __name__, url_prefix='/forms')


class OrderForm(FlaskForm):
    sum = FloatField('Sum', validators=[DataRequired()])
    cur = StringField('Cur', validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    market = StringField('Market', validators=[DataRequired()])
    isin = StringField('ISIN', validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])


@forms.route('/order', methods=('GET', 'POST'))
def submit():
    form = OrderForm()
    if form.validate_on_submit():
        return redirect('/tables/orders')
    return templating.render_template('form.html', form=form)
