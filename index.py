# -*- coding: utf-8 -*-

from coincheck import account, market, order
import gspread
import oauth2client.client
import datetime
import re

import settings

ACCESS_KEY = settings.ACCESS_KEY
SECRET_KEY = settings.SECRET_KEY

client_email = settings.CLIENT_EMAIL
private_key = settings.PRIVATE_KEY.replace('\\n', '\n')

SELL_MARGIN = 2000
BUY_MARGUN = 5000
DIFFERENCE = 1000

m = market.Market()
o = order.Order(
    access_key=ACCESS_KEY,
    secret_key=SECRET_KEY
)
a = account.Account(
    access_key=ACCESS_KEY,
    secret_key=SECRET_KEY
)

balance = a.get_balance()
AMOUNT = round(float(balance['jpy']) / 10 ** 7 / 2, 3)


def get_market(wb):

    data = m.ticker()
    test_time = datetime.datetime.fromtimestamp(data['timestamp'])
    rate = int(data['last'])

    sheet = wb.worksheet("ticker")
    all_values = sheet.get_all_values()
    row_num = int(len(all_values)) - 1
    differnce1 = rate - int(all_values[1][1])
    differnce2 = rate - int(all_values[2][1])
    differnce_sum = differnce1 + differnce2
    data_list = [test_time, data['last'],
                 differnce1, differnce2, differnce_sum]

    sheet.delete_row(row_num + 1)
    sheet.insert_row(data_list, index=2)
    print("ticker sheet complete")

    buy = True
    sell = True

    # 合計が上がっている時
    if differnce_sum > DIFFERENCE:
        sell = False

    # 合計が下がっている時
    if differnce_sum < -DIFFERENCE:
        buy = False

    if AMOUNT < 0.005:
        buy = False

    return {"buy": buy, "sell": sell}


def test_account():
    data = a.get_balance()
    print("jpy", round(float(data['jpy'])))
    print("btc", round(float(data['btc'])))


def test_order(wb, judge):
    sheet_buy = wb.worksheet("buy")
    sheet_sell = wb.worksheet("sell")
    all_values = sheet_buy.get_all_values()
    all_sell = sheet_sell.get_all_values()
    rate = float(m.ticker()['last'])
    buy_rate_list = []
    print("Now rate is", rate)

    print("Sell is", judge['sell'])
    for index, record in reversed(list(enumerate(all_values))):
        if index == 0:
            continue
        buy_rate_list.append(float(record[4]))
        if judge['sell']:
            sell_btc(all_sell, sheet_buy, sheet_sell, rate, record, index)

    all_values = sheet_buy.get_all_values()

    print("Buy is", judge['buy'])
    if judge['buy']:
        # btcがゼロの時
        if len(all_values) <= 1:
            buy_btc(all_values, sheet_buy, rate)
            print("buy btc by", rate)
            return
        #
        if min(buy_rate_list) - BUY_MARGUN > rate:
            buy_btc(all_values, sheet_buy, rate)
            print("buy btc by", rate)
            return

        if max(buy_rate_list) + BUY_MARGUN < rate:
            buy_btc(all_values, sheet_buy, rate)
            print("buy btc by", rate)
            return

    print("Nothing to buy")


def buy_btc(all_values, sheet, rate):
    result = o.buy_btc_jpy(rate=rate + 1000, amount=AMOUNT)
    cells = [result['id'], fix_date(
        result['created_at']), result['success'], result['amount'], rate]
    sheet.insert_row(cells, index=len(all_values) + 1)


def sell_btc(all_sell, sheet_buy, sheet_sell, rate, record, index):
    buy_rate = float(record[4])
    amount = float(record[3])

    if rate > buy_rate + SELL_MARGIN:
        result = o.sell_btc_jpy(rate=rate - 1000, amount=amount)
        print(result)

        if result['success']:
            profit = rate * amount - buy_rate * amount
            cells = [
                result['id'],
                fix_date(result['created_at']),
                result['success'],
                result['amount'],
                rate,
                profit,
            ]
            sheet_sell.insert_row(cells, index=2)
            sheet_buy.delete_row(index + 1)
            print(buy_rate, "was sold!!!!")
            return

    else:
        print(buy_rate, "was not sold.")


def login_gspread():
    scope = ['https://spreadsheets.google.com/feeds']
    credentials = oauth2client.client.SignedJwtAssertionCredentials(
        client_email, private_key.encode(), scope)
    gc = gspread.authorize(credentials)
    return gc.open_by_key('1ZO2qmqLvbKqU3VCft80PCaj9xYL0XKbOidcdWzJCLm8')


def fix_date(created_at):
    result = re.sub('\..*', "", created_at)
    date = datetime.datetime.strptime(result, '%Y-%m-%dT%H:%M:%S')
    return date + datetime.timedelta(hours=9)


if __name__ == "__main__":
    print(AMOUNT)
    wb = login_gspread()
    judge = get_market(wb)
    test_order(wb, judge)
