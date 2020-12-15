from pprint import pprint
from datetime import datetime

from base import date_to_key
from portfolio import Portfolio


portfolio = Portfolio(1)
#portfolio = Portfolio(1, broker_id=2)

# 2019-11-20
#start_date = datetime(2019, 11, 20)
start_date = datetime(2020, 2, 10)
#end_date = datetime(2020, 12, 11)
end_date = datetime.now()

#pprint(portfolio.get_value())
#portfolio.chart_cbr(start_date, end_date, currency=Portfolio.RUB)
#portfolio.chart_cbr(start_date, end_date, currency=Portfolio.USD)
portfolio.chart_profit(start_date, end_date, currency=Portfolio.RUB)
#portfolio.chart_profit(start_date, end_date, currency=Portfolio.USD)
