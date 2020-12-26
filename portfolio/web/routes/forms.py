from flask import Blueprint, templating
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, DateField, IntegerField
from wtforms.validators import DataRequired


forms = Blueprint('forms', __name__, url_prefix='/')


class OrderForm(FlaskForm):
    sum = FloatField('Sum', validators=[DataRequired()])
    cur = StringField('Cur', validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    market = StringField('Market', validators=[DataRequired()])
    isin = StringField('ISIN', validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])


@forms.route('/', methods=('GET', 'POST'))
def submit():
    form = OrderForm()
    #if form.validate_on_submit():
    #    return redirect('/success')
    return templating.render_template('form.html', form=form)
