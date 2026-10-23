import boto3, json, base64, hashlib, calendar, urllib.parse
from datetime import datetime, timezone, timedelta
# ReturnURL: the FIRST charge of the recurring order. The source of truth for activation.
_sm = boto3.client("secretsmanager")
_sqs = boto3.client("sqs")
ddb = boto3.resource("dynamodb").Table("subscriptions")
QURL = None


def ecpay_url_encode(s):
    e = urllib.parse.quote_plus(str(s)).replace("~", "%7E").lower()
    for o, n in (("%2d", "-"), ("%5f", "_"), ("%2e", "."), ("%21", "!"), ("%2a", "*"), ("%28", "("), ("%29", ")")):
        e = e.replace(o, n)
    return e


def gen_cmv(params, hash_key, hash_iv):
    items = {k: v for k, v in params.items() if k != "CheckMacValue"}  # keep "" values (ECPay signs them)
    body = "&".join(f"{k}={items[k]}" for k in sorted(items, key=str.lower))
    return hashlib.sha256(ecpay_url_encode(f"HashKey={hash_key}&{body}&HashIV={hash_iv}").encode()).hexdigest().upper()


def text(body, code=200):
    return {"statusCode": code, "headers": {"Content-Type": "text/plain; charset=utf-8"}, "body": body}


def add_period(dt, ptype, freq):
    if ptype == "D":
        return dt + timedelta(days=freq)
    m = dt.month - 1 + freq
    y, m = dt.year + m // 12, m % 12 + 1
    return dt.replace(year=y, month=m, day=min(dt.day, calendar.monthrange(y, m)[1]))


def handler(event, context):
    raw = event.get("body") or ""
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode()
    p = dict(urllib.parse.parse_qsl(raw, keep_blank_values=True))
    s = json.loads(_sm.get_secret_value(SecretId="flight/ecpay")["SecretString"])
    mine = gen_cmv(p, s["hash_key"], s["hash_iv"])
    if p.get("MerchantID") != s["merchant_id"] or p.get("CheckMacValue", "").upper() != mine:
        print("REJECT CheckMacValueInvalid", p.get("MerchantID"), p.get("MerchantTradeNo"), "got", p.get("CheckMacValue"), "want", mine)
        return text("0|CheckMacValueInvalid", 400)
    trade_no, email, route = p.get("MerchantTradeNo"), p.get("CustomField1", ""), p.get("CustomField2", "")
    print("CMV verified", trade_no, email, route, "RtnCode", p.get("RtnCode"), p.get("RtnMsg"), "SimulatePaid", p.get("SimulatePaid"))
    if p.get("SimulatePaid") == "1":
        print("SimulatePaid=1: ack only, not activating")
        return text("1|OK")
    if p.get("RtnCode") != "1":
        print("first charge failed, row stays pending_payment")
        return text("1|OK")
    key = {"email": email, "route": route}
    row = ddb.get_item(Key=key).get("Item")
    if not row:
        print("no subscription row for", key)
        return text("1|OK")
    now = datetime.now(timezone.utc)
    end = add_period(now, row.get("period_type", "M"), int(row.get("frequency", 1)))
    try:
        ddb.update_item(
            Key=key,
            UpdateExpression="SET subscription_status=:a, merchant_trade_no=:m, current_period_end=:e, current_period_end_date=:ed, "
                             "activated_at=:n, total_success_times=:one, failed_attempts=:zero",
            ConditionExpression="NOT (subscription_status = :a AND merchant_trade_no = :m)",
            ExpressionAttributeValues={":a": "active", ":m": trade_no, ":e": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                       ":ed": end.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"),
                                       ":n": now.strftime("%Y-%m-%dT%H:%M:%SZ"), ":one": 1, ":zero": 0})
    except ddb.meta.client.exceptions.ConditionalCheckFailedException:
        print("already active for", trade_no, "- duplicate callback, ack only")
        return text("1|OK")
    print("UpdateItem -> active", key, "until", end.isoformat())
    global QURL
    if QURL is None:
        QURL = _sqs.get_queue_url(QueueName="flight-status-queue")["QueueUrl"]
    _sqs.send_message(QueueUrl=QURL, MessageBody=json.dumps({"event_type": "welcome", "email": email, "route": route,
                                                              "merchant_trade_no": trade_no, "amount": p.get("TradeAmt") or s.get("amount"),
                                                              "current_period_end_date": end.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")}))
    return text("1|OK")
