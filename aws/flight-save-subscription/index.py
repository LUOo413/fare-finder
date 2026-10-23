import boto3, json, base64, re, html, hashlib, secrets, urllib.parse
from datetime import datetime, timezone, timedelta
from decimal import Decimal
PLANS = {"tokyo": {"origin": "TPE", "destination": "TYO", "city": "東京"}, "seoul": {"origin": "TPE", "destination": "SEL", "city": "首爾"}, "london": {"origin": "TPE", "destination": "LON", "city": "倫敦"}}
API = "https://hyyhuk76jc.execute-api.us-east-1.amazonaws.com"
# Monthly. To test renewals next day, temporarily set ("D", 1, 2) and redeploy.
PERIOD_TYPE, FREQUENCY, EXEC_TIMES = "M", 1, 999
ddb = boto3.resource("dynamodb").Table("subscriptions")
_sm = boto3.client("secretsmanager")
H = {"Content-Type": "application/json"}
TPE = timezone(timedelta(hours=8))


def resp(code, obj):
    return {"statusCode": code, "headers": H, "body": json.dumps(obj, ensure_ascii=False)}


def num(v):
    return int(v) if v == v.to_integral() else float(v)


def ecpay_url_encode(s):
    e = urllib.parse.quote_plus(str(s)).replace("~", "%7E").lower()
    for o, n in (("%2d", "-"), ("%5f", "_"), ("%2e", "."), ("%21", "!"), ("%2a", "*"), ("%28", "("), ("%29", ")")):
        e = e.replace(o, n)
    return e


def gen_cmv(params, hash_key, hash_iv):
    items = {k: v for k, v in params.items() if k != "CheckMacValue"}  # keep "" values (ECPay signs them)
    body = "&".join(f"{k}={items[k]}" for k in sorted(items, key=str.lower))
    return hashlib.sha256(ecpay_url_encode(f"HashKey={hash_key}&{body}&HashIV={hash_iv}").encode()).hexdigest().upper()


def checkout_form(s, trade_no, email, route, city):
    host = "payment-stage.ecpay.com.tw" if s.get("env", "stage") == "stage" else "payment.ecpay.com.tw"
    amount = str(int(s["amount"]))
    p = {"MerchantID": s["merchant_id"], "MerchantTradeNo": trade_no,
         "MerchantTradeDate": datetime.now(TPE).strftime("%Y/%m/%d %H:%M:%S"),
         "PaymentType": "aio", "ChoosePayment": "Credit", "EncryptType": "1",
         "TotalAmount": amount, "PeriodAmount": amount,
         "PeriodType": PERIOD_TYPE, "Frequency": str(FREQUENCY), "ExecTimes": str(EXEC_TIMES),
         "ItemName": f"機票降價通知 月訂閱（台北-{city}）", "TradeDesc": "Flight price alert monthly plan",
         "ReturnURL": API + "/ecpay-return", "PeriodReturnURL": API + "/ecpay-period",
         "OrderResultURL": API + "/ecpay-result",
         "CustomField1": email, "CustomField2": route}
    p["CheckMacValue"] = gen_cmv(p, s["hash_key"], s["hash_iv"])
    inputs = "".join(f'<input type="hidden" name="{k}" value="{html.escape(v, quote=True)}">' for k, v in p.items())
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>前往綠界付款</title></head><body>'
            f'<p>正在前往綠界付款頁…</p><form method="post" action="https://{host}/Cashier/AioCheckOut/V5">{inputs}</form>'
            '<script>document.forms[0].submit()</script></body></html>')


def handler(event, context):
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode()
    try:
        b = json.loads(raw)
    except Exception:
        return resp(400, {"error": "invalid JSON"})
    email = str(b.get("email", "")).strip().lower()
    plan = b.get("plan_name")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) or len(email) > 50:
        return resp(400, {"error": "invalid email"})
    if plan not in PLANS:
        return resp(400, {"error": "unknown plan_name"})
    try:
        tp = Decimal(str(b.get("target_price")))
    except Exception:
        return resp(400, {"error": "target_price must be a number"})
    if not tp.is_finite() or tp <= 0 or tp > 1000000:
        return resp(400, {"error": "target_price must be a positive number"})
    p = PLANS[plan]
    route = p["origin"] + "-" + p["destination"]
    key = {"email": email, "route": route}
    now = datetime.now(timezone.utc)
    now_s = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    row = ddb.get_item(Key=key).get("Item") or {}
    status = row.get("subscription_status")
    paid = status == "active" or (status == "cancelled" and row.get("current_period_end", "") >= now_s)
    names = {"#pn": "plan_name", "#o": "origin", "#d": "destination", "#tp": "target_price", "#c": "currency", "#u": "updated_at", "#ca": "created_at"}
    values = {":p": plan, ":o": p["origin"], ":d": p["destination"], ":t": tp, ":c": "TWD", ":u": now.isoformat()}
    expr = "SET #pn=:p, #o=:o, #d=:d, #tp=:t, #c=:c, #u=:u, #ca=if_not_exists(#ca,:u)"
    if paid:
        # Paid (or cancelled but still inside the paid period): update the target in place, no re-payment.
        ddb.update_item(Key=key, UpdateExpression=expr, ExpressionAttributeNames=names, ExpressionAttributeValues=values)
        return resp(200, {**key, "ok": True, "plan_name": plan, "target_price": num(tp), "currency": "TWD",
                          "subscription_status": status, "current_period_end": row.get("current_period_end"),
                          "current_period_end_date": row.get("current_period_end_date")})
    s = json.loads(_sm.get_secret_value(SecretId="flight/ecpay")["SecretString"])
    trade_no = "FF" + datetime.now(TPE).strftime("%y%m%d%H%M%S") + secrets.token_hex(3).upper()
    names.update({"#s": "subscription_status", "#m": "merchant_trade_no", "#pt": "period_type", "#f": "frequency"})
    values.update({":s": "pending_payment", ":m": trade_no, ":pt": PERIOD_TYPE, ":f": FREQUENCY})
    ddb.update_item(Key=key, UpdateExpression=expr + ", #s=:s, #m=:m, #pt=:pt, #f=:f",
                    ExpressionAttributeNames=names, ExpressionAttributeValues=values)
    print("pending_payment", email, route, trade_no)
    return {"statusCode": 200, "headers": {"Content-Type": "text/html; charset=utf-8"},
            "body": checkout_form(s, trade_no, email, route, p["city"])}
