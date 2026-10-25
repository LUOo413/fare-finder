import os, json, html, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key

UA = "Mozilla/5.0 (compatible; flight-notifier/1.0)"
FLOOR_H = float(os.environ.get("NOTIFY_FLOOR_HOURS", "24"))
REALERT_PCT = float(os.environ.get("REALERT_PCT", "20"))
REALERT_ABS = float(os.environ.get("REALERT_ABS_TWD", "2000"))
CITY = {"TPE": "台北", "TYO": "東京", "SEL": "首爾", "LON": "倫敦"}
_sm = boto3.client("secretsmanager")
_hist = boto3.resource("dynamodb").Table("notification_history")
_secret = None


class Transient(Exception):
    pass


def resend_secret():
    global _secret
    if _secret is None:
        _secret = json.loads(_sm.get_secret_value(SecretId="flight/resend")["SecretString"])
    return _secret


def _ddmm(iso):
    return iso[8:10] + iso[5:7] if iso and len(iso) >= 10 else ""


def booking_url(fare, origin, destination, marker=None):
    path = origin + _ddmm(fare.get("depart_date")) + destination + _ddmm(fare.get("return_date"))
    url = "https://www.aviasales.com/search/" + path
    return url + ("?marker=" + str(marker) if marker else "")


def _names(route):
    o, d = route.split("-")
    return o, d, CITY.get(o, o), CITY.get(d, d)


def subject(route, fare):
    _, _, on, dn = _names(route)
    return f"✈️ {on} → {dn} 降價通知！NT${fare['price']:,} 已達標"


def render_text(route, fare, target_price, usd_price=None, marker=None):
    o, d, on, dn = _names(route)
    lines = [f"{on} → {dn} 機票降價了！", "",
             f"目前最低價：NT${fare['price']:,}" + (f"（約 US${usd_price:,}）" if usd_price else ""),
             f"你的目標價：NT${target_price:,}",
             f"航空公司：{fare.get('airline') or '-'}",
             f"去程：{(fare.get('depart_date') or '')[:10]}　回程：{(fare.get('return_date') or '')[:10]}", "",
             "立即訂購：" + booking_url(fare, o, d, marker), "",
             "— Flight Price Notifier"]
    return "\n".join(lines)


def render_html(route, fare, target_price, usd_price=None, marker=None):
    o, d, on, dn = _names(route)
    e = html.escape
    usd = f'<p style="margin:4px 0 0;color:#555;font-size:14px">約 US${usd_price:,}</p>' if usd_price else ""
    return (
        '<div style="font-family:Arial,Helvetica,sans-serif;max-width:520px;margin:0 auto;color:#1a1a1a">'
        f'<h2 style="margin:0 0 12px">{e(on)} → {e(dn)} 機票降價了！</h2>'
        f'<p style="margin:0;font-size:28px;font-weight:bold">NT${fare["price"]:,}</p>{usd}'
        f'<p style="margin:16px 0 4px">你的目標價：NT${target_price:,}</p>'
        f'<p style="margin:4px 0">航空公司：{e(str(fare.get("airline") or "-"))}</p>'
        f'<p style="margin:4px 0">去程：{e((fare.get("depart_date") or "")[:10])}　回程：{e((fare.get("return_date") or "")[:10])}</p>'
        f'<p style="margin:24px 0"><a href="{e(booking_url(fare, o, d, marker))}" '
        'style="background:#1f4e79;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;display:inline-block">立即訂購</a></p>'
        '<p style="color:#888;font-size:12px">Flight Price Notifier — 你收到這封信是因為你訂閱了這條航線的降價通知。</p>'
        '</div>')


def should_send(pk, new_price):
    r = _hist.query(KeyConditionExpression=Key("pk").eq(pk), ScanIndexForward=False, Limit=1)["Items"]
    if not r:
        return True, "first alert"
    last = r[0]
    sent = datetime.fromisoformat(last["sent_at"])
    if datetime.now(timezone.utc) - sent >= timedelta(hours=FLOOR_H):
        return True, "floor elapsed"
    lp = float(last.get("price", 0))
    if new_price <= lp * (1 - REALERT_PCT / 100) or (lp - new_price) >= REALERT_ABS:
        return True, f"big drop {lp} -> {new_price}"
    return False, f"last {lp} at {last['sent_at']}"


def send_email(msg_to, subj, html_body, text_body):
    s = resend_secret()
    body = {"from": s["from"], "to": [msg_to], "subject": subj, "html": html_body, "text": text_body}
    if s.get("reply_to"):
        body["reply_to"] = s["reply_to"]
    req = urllib.request.Request("https://api.resend.com/emails", data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": "Bearer " + s["api_key"],
                                          "Content-Type": "application/json", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as ex:
        return ex.code, ex.read().decode()
    except urllib.error.URLError as ex:
        raise Transient(repr(ex))


def process(m):
    email, route = m["email"], m["route"]
    fare = m["cheapest"]
    price = fare["price"]
    pk = f"{email}#{route}"
    ok, why = should_send(pk, price)
    if not ok:
        print("skipped (deduped)", pk, price, why)
        return
    usd = (m.get("cheapest_usd") or {}).get("price")
    tp = int(m["target_price"])
    status, text = send_email(email, subject(route, fare), render_html(route, fare, tp, usd),
                              render_text(route, fare, tp, usd))
    if 200 <= status < 300:
        _hist.put_item(Item={"pk": pk, "sent_at": datetime.now(timezone.utc).isoformat(), "email": email,
                             "route": route, "price": Decimal(str(price)), "currency": "TWD"})
        print("sent", pk, price, why, text)
    elif status == 429 or status >= 500:
        raise Transient(f"resend {status} {text}")
    else:
        print("dropped (permanent)", pk, status, text)


def handler(event, context):
    failures = []
    for rec in event.get("Records", []):
        try:
            process(json.loads(rec["body"]))
        except Transient as ex:
            print("transient, will retry", rec.get("messageId"), ex)
            failures.append({"itemIdentifier": rec["messageId"]})
    return {"batchItemFailures": failures}
