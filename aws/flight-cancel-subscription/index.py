import boto3, json, base64, re, time, hashlib, calendar, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
# POST /cancel {email, route}: stop future ECPay charges, keep alerts until current_period_end (grace).
_sm = boto3.client("secretsmanager")
_sqs = boto3.client("sqs")
ddb = boto3.resource("dynamodb").Table("subscriptions")
H = {"Content-Type": "application/json"}
QURL = None


def resp(code, obj):
    return {"statusCode": code, "headers": H, "body": json.dumps(obj, ensure_ascii=False)}


def ecpay_url_encode(s):
    e = urllib.parse.quote_plus(str(s)).replace("~", "%7E").lower()
    for o, n in (("%2d", "-"), ("%5f", "_"), ("%2e", "."), ("%21", "!"), ("%2a", "*"), ("%28", "("), ("%29", ")")):
        e = e.replace(o, n)
    return e


def gen_cmv(params, hash_key, hash_iv):
    items = {k: v for k, v in params.items() if k != "CheckMacValue"}  # keep "" values (ECPay signs them)
    body = "&".join(f"{k}={items[k]}" for k in sorted(items, key=str.lower))
    return hashlib.sha256(ecpay_url_encode(f"HashKey={hash_key}&{body}&HashIV={hash_iv}").encode()).hexdigest().upper()


def add_month(dt):
    y, m = (dt.year + 1, 1) if dt.month == 12 else (dt.year, dt.month + 1)
    return dt.replace(year=y, month=m, day=min(dt.day, calendar.monthrange(y, m)[1]))


def ecpay_cancel(s, trade_no):
    host = "payment-stage.ecpay.com.tw" if s.get("env", "stage") == "stage" else "payment.ecpay.com.tw"
    p = {"MerchantID": s["merchant_id"], "MerchantTradeNo": trade_no, "Action": "Cancel", "TimeStamp": str(int(time.time()))}
    p["CheckMacValue"] = gen_cmv(p, s["hash_key"], s["hash_iv"])
    req = urllib.request.Request(f"https://{host}/Cashier/CreditCardPeriodAction", data=urllib.parse.urlencode(p).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            out = r.read().decode()
    except (urllib.error.URLError, OSError) as ex:
        return {"RtnCode": "network_error", "RtnMsg": repr(ex)}
    return dict(urllib.parse.parse_qsl(out, keep_blank_values=True)) or {"RtnCode": "unparsed", "RtnMsg": out[:200]}


def handler(event, context):
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode()
    try:
        b = json.loads(raw)
    except Exception:
        return resp(400, {"error": "invalid JSON"})
    email = str(b.get("email", "")).strip().lower()
    route = str(b.get("route", "")).strip().upper()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) or not re.match(r"^[A-Z]{3}-[A-Z]{3}$", route):
        return resp(400, {"error": "invalid email or route"})
    key = {"email": email, "route": route}
    row = ddb.get_item(Key=key).get("Item")
    if not row:
        return resp(404, {"error": "subscription not found"})
    status = row.get("subscription_status")
    if status == "cancelled":
        return resp(200, {**key, "ok": True, "subscription_status": "cancelled",
                          "current_period_end": row.get("current_period_end"), "current_period_end_date": row.get("current_period_end_date")})
    if status != "active":
        return resp(409, {"error": f"subscription is {status or 'not paid'}, nothing to cancel"})
    s = json.loads(_sm.get_secret_value(SecretId="flight/ecpay")["SecretString"])
    trade_no = row.get("merchant_trade_no")
    r = ecpay_cancel(s, trade_no)
    # 90100150 = order unknown to ECPay (e.g. a synthetic test order): expected on stage, still cancel locally.
    print("ECPay CreditCardPeriodAction Cancel", trade_no, "->", r.get("RtnCode"), r.get("RtnMsg"))
    now = datetime.now(timezone.utc)
    end_s, end_d = row.get("current_period_end"), row.get("current_period_end_date")
    if not end_s:
        end = add_month(now)
        end_s, end_d = end.strftime("%Y-%m-%dT%H:%M:%SZ"), end.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    ddb.update_item(Key=key,
                    UpdateExpression="SET subscription_status=:c, cancelled_at=:n, current_period_end=:e, current_period_end_date=:ed, ecpay_cancel_result=:r",
                    ExpressionAttributeValues={":c": "cancelled", ":n": now.strftime("%Y-%m-%dT%H:%M:%SZ"), ":e": end_s, ":ed": end_d,
                                               ":r": f"{r.get('RtnCode')} {r.get('RtnMsg')}"[:200]})
    print("UpdateItem -> cancelled", key, "service until", end_s)
    global QURL
    if QURL is None:
        QURL = _sqs.get_queue_url(QueueName="flight-status-queue")["QueueUrl"]
    _sqs.send_message(QueueUrl=QURL, MessageBody=json.dumps({"event_type": "cancel", "email": email, "route": route,
                                                              "merchant_trade_no": trade_no, "current_period_end_date": end_d}))
    return resp(200, {**key, "ok": True, "subscription_status": "cancelled", "current_period_end": end_s,
                      "current_period_end_date": end_d, "ecpay": r.get("RtnCode")})
