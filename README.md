Mongo cheat sheet

rename field: db.orders.update({}, {$rename:{"name":"isin"}}, false, true);

update field: db.money.update({broker: 1.0}, {$set: {broker: NumberInt(1)}}, false, true)

add field: db.quotes.update({}, {$set:{"interval":"day"}}, false, true);
