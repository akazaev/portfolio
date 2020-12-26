from datetime import datetime

import cProfile

from portfolio.portfolio import Portfolio

portfolio = Portfolio(1)

# 2019-11-20
start_date = datetime(2019, 11, 20)
end_date = datetime(2020, 11, 25)

#cProfile.run("portfolio.cbr(start_date, end_date)", sort='cumtime')
cProfile.run("portfolio.get_value()", sort='cumtime')
