import boto3, json, base64, hashlib, calendar, urllib.parse
from datetime import datetime, timezone, timedelta
# PeriodReturnURL: every charge from the 2nd onward. Success extends the paid period;
# failures are counted and only the 6th in a row (ECPay terminates the contract) expires the row.
_sm = boto3.client("secretsmanager")
ddb = boto3.resource("dynamodb").Table("subscriptions")
MAX_FAILS = 6


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
    print("CMV verified", trade_no, email, route, "RtnCode", p.get("RtnCode"), p.get("RtnMsg"),
          "TotalSuccessTimes", p.get("TotalSuccessTimes"), "SimulatePaid", p.get("SimulatePaid"))
    if p.get("SimulatePaid") == "1":
        print("SimulatePaid=1: ack only, no bookkeeping")
        return text("1|OK")
    key = {"email": email, "route": route}
    row = ddb.get_item(Key=key).get("Item")
    if not row or row.get("merchant_trade_no") != trade_no:
        print("no row for this order (row trade no:", row and row.get("merchant_trade_no"), ") - ack only")
        return text("1|OK")
    now = datetime.now(timezone.utc)
    if p.get("RtnCode") == "1":
        times = int(p.get("TotalSuccessTimes") or 0)
        if times and times <= int(row.get("total_success_times", 0)):
            print("renewal", times, "already recorded - duplicate, ack only")
            return text("1|OK")
        base = max(now, datetime.strptime(row.get("current_period_end", "1970-01-01T00:00:00Z"), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc))
        end = add_period(base, row.get("period_type", "M"), int(row.get("frequency", 1)))
        status = "cancelled" if row.get("subscription_status") == "cancelled" else "active"
        ddb.update_item(Key=key,
                        UpdateExpression="SET subscription_status=:s, current_period_end=:e, current_period_end_date=:ed, "
                                         "last_charged_at=:n, total_success_times=:t, failed_attempts=:zero",
                        ExpressionAttributeValues={":s": status, ":e": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                   ":ed": end.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"),
                                                   ":n": now.strftime("%Y-%m-%dT%H:%M:%SZ"), ":t": times, ":zero": 0})
        print("renewal ok ->", status, "until", end.isoformat(), "TotalSuccessTimes", times)
        return text("1|OK")
    fails = int(row.get("failed_attempts", 0)) + 1
    if fails >= MAX_FAILS:
        ddb.update_item(Key=key, UpdateExpression="SET subscription_status=:x, failed_attempts=:f",
                        ExpressionAttributeValues={":x": "expired", ":f": fails})
        print("renewal failed", fails, "times in a row - ECPay ended the contract -> expired")
    else:
        ddb.update_item(Key=key, UpdateExpression="SET failed_attempts=:f", ExpressionAttributeValues={":f": fails})
        print("renewal failed (attempt", fails, ") - ECPay will retry, status unchanged")
    return text("1|OK")
