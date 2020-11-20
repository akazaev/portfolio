from datetime import datetime

from portfolio import Portfolio


portfolio = Portfolio(1)

# 2019-11-20
#start_date = datetime(2019, 11, 20)
start_date = datetime(2020, 10, 1)
end_date = datetime(2020, 11, 19)

portfolio.chart_cbr(start_date, end_date)
