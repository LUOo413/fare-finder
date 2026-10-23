import os, json, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Attr

UA = "Mozilla/5.0 (compatible; flight-notifier/1.0)"
_sm = boto3.client("secretsmanager")
_sqs = boto3.client("sqs")
_tbl = boto3.resource("dynamodb").Table("subscriptions")
QURL = None


def next_month():
    now = datetime.now(timezone.utc)
    y, m = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
    return f"{y:04d}-{m:02d}"


def fetch_cheapest(origin, destination, month, token, currency):
    q = urllib.parse.urlencode({"origin": origin, "destination": destination, "depart_date": month,
                                "currency": currency, "token": token})
    req = urllib.request.Request(f"https://api.travelpayouts.com/v1/prices/cheap?{q}",
                                 headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = json.loads(r.read())
    except (urllib.error.URLError, ValueError) as ex:
        print("travelpayouts error", currency, origin, destination, repr(ex))
        return None
    if not body.get("success") or not body.get("data"):
        return None
    offers = body["data"].get(destination, {})
    if not offers:
        return None
    best = min(offers.values(), key=lambda o: o["price"])
    return {"price": best["price"], "currency": currency.upper(), "airline": best.get("airline"),
            "depart_date": best.get("departure_at"), "return_date": best.get("return_at")}


def scan_route(route):
    items, kw = [], {"FilterExpression": Attr("route").eq(route)}
    while True:
        page = _tbl.scan(**kw)
        items += page.get("Items", [])
        if "LastEvaluatedKey" not in page:
            return items
        kw["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def paid(it, now_s):
    """Paywall gate: serve active rows and cancelled rows still inside their paid period."""
    status, end = it.get("subscription_status"), it.get("current_period_end", "")
    if status == "active":
        return True
    if status == "cancelled":
        if end >= now_s:
            print("gate: cancelled, in grace until", end, it["email"])
            return True
        _tbl.update_item(Key={"email": it["email"], "route": it["route"]},
                         UpdateExpression="SET subscription_status=:x",
                         ConditionExpression="subscription_status = :c",
                         ExpressionAttributeValues={":x": "expired", ":c": "cancelled"})
        print("gate: cancelled and period ended", end, "-> expired", it["email"])
        return False
    print("gate: skip", status or "no status (unpaid M1 row)", it["email"])
    return False


def handler(event, context):
    global QURL
    origin, destination = event["origin"], event["destination"]
    route = event.get("route") or f"{origin}-{destination}"
    token = json.loads(_sm.get_secret_value(SecretId="flight/travelpayouts")["SecretString"])["token"]
    month = next_month()

    tw = fetch_cheapest(origin, destination, month, token, "twd")
    if not tw:
        print("no TWD fare for", route, month, "(empty/429) - skipping")
        return {"ok": True, "route": route, "matched": 0}
    us = fetch_cheapest(origin, destination, month, token, "usd")
    print(route, month, "cheapest", tw["price"], "TWD", tw["airline"],
          "| USD", us["price"] if us else "n/a")

    if QURL is None:
        QURL = _sqs.get_queue_url(QueueName="flight-fare-queue")["QueueUrl"]
    matched = 0
    now_s = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for it in scan_route(route):
        if not paid(it, now_s):
            continue
        tp = it.get("target_price")
        if tp is None or Decimal(tp) < Decimal(str(tw["price"])):
            continue
        body = {"email": it["email"], "route": route, "plan_name": it.get("plan_name"),
                "target_price": int(tp),
                "cheapest": {"price": tw["price"], "currency": "TWD", "airline": tw["airline"],
                             "depart_date": tw["depart_date"], "return_date": tw["return_date"]}}
        if us:
            body["cheapest_usd"] = {"price": us["price"], "currency": "USD", "airline": us["airline"],
                                    "depart_date": us["depart_date"], "return_date": us["return_date"]}
        _sqs.send_message(QueueUrl=QURL, MessageBody=json.dumps(body))
        matched += 1
    print(route, "matched", matched, "subscriber(s)")
    return {"ok": True, "route": route, "cheapest_twd": tw["price"], "matched": matched}
