from portfolio.secret import *

API_URL = 'https://api-invest.tinkoff.ru/openapi/sandbox'
ISS_API_URL = 'https://iss.moex.com'


CBR_BASE_RATE = 6.5
CBR_RATE = {
    (2019, 12, 16): 6.25,
    (2020, 2, 10): 6,
    (2020, 4, 27): 5.5,
    (2020, 6, 22): 4.5,
    (2020, 7, 27): 4.25,
}

MONGO_URL = 'mongodb://localhost:27017/'
