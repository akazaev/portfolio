Mongo cheat sheet

rename field: db.orders.update({}, {$rename:{"name":"isin"}}, false, true);

update field: db.money.update({cur: "RUB"}, {$set: {cur: "rub"}}, false, true);

