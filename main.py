from datetime import datetime
from portfolio.portfolio import Portfolio

portfolio = Portfolio(1)
start_date = datetime(2019, 11, 20)
end_date = datetime.now()
portfolio.chart(start_date, end_date, currency=Portfolio.RUB)
