import json, html, urllib.request, urllib.error
from datetime import datetime, timezone
import boto3
from boto3.dynamodb.conditions import Key
# The ONE consumer of flight-status-queue. Routes on event_type: "welcome" (paid) or "cancel".
UA = "Mozilla/5.0 (compatible; flight-notifier/1.0)"
SITE = "https://fare-finder-ruddy.vercel.app/app"
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


def route_name(route):
    o, d = route.split("-")
    return f"{CITY.get(o, o)} → {CITY.get(d, d)}"


def render(m):
    rn, until = route_name(m["route"]), m.get("current_period_end_date") or ""
    if m["event_type"] == "welcome":
        subj = f"✈️ 訂閱成功：{rn} 機票降價通知已啟用"
        lines = [f"謝謝你的訂閱！{rn} 的降價通知已經啟用。",
                 f"月費：NT${m.get('amount') or ''}，每月自動扣款。本期有效至 {until}。",
                 "票價低於你的目標價時，我們會寄 email 通知你。"]
    else:
        subj = f"訂閱已取消：{rn} 機票降價通知"
        lines = [f"你已取消 {rn} 的降價通知訂閱，之後不會再扣款。",
                 f"已付費的這一期仍然有效，到 {until} 為止你還是會收到降價通知。",
                 "想再訂閱的話，隨時回到網站重新訂閱即可。"]
    text = "\n".join(lines + ["", "管理訂閱：" + SITE, "", "— Flight Price Notifier"])
    body = "".join(f'<p style="margin:8px 0">{html.escape(x)}</p>' for x in lines)
    page = ('<div style="font-family:Arial,Helvetica,sans-serif;max-width:520px;margin:0 auto;color:#1a1a1a">'
            f'<h2 style="margin:0 0 12px">{html.escape(subj)}</h2>{body}'
            f'<p style="margin:24px 0"><a href="{SITE}" style="background:#1f4e79;color:#fff;padding:12px 24px;'
            'border-radius:6px;text-decoration:none;display:inline-block">管理訂閱</a></p>'
            '<p style="color:#888;font-size:12px">Flight Price Notifier</p></div>')
    return subj, page, text


def send_email(to, subj, html_body, text_body):
    s = resend_secret()
    body = {"from": s["from"], "to": [to], "subject": subj, "html": html_body, "text": text_body}
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
    if m.get("event_type") not in ("welcome", "cancel"):
        print("dropped: unknown event_type", m)
        return
    pk = f"status#{m['event_type']}#{m['email']}#{m['route']}#{m.get('merchant_trade_no')}"
    if _hist.query(KeyConditionExpression=Key("pk").eq(pk), Limit=1)["Items"]:
        print("skipped (already sent)", pk)
        return
    subj, page, text = render(m)
    status, out = send_email(m["email"], subj, page, text)
    if 200 <= status < 300:
        _hist.put_item(Item={"pk": pk, "sent_at": datetime.now(timezone.utc).isoformat(), "email": m["email"],
                             "route": m["route"], "event_type": m["event_type"]})
        print("sent", pk, out)
    elif status == 429 or status >= 500:
        raise Transient(f"resend {status} {out}")
    else:
        print("dropped (permanent)", pk, status, out)


def handler(event, context):
    failures = []
    for rec in event.get("Records", []):
        try:
            process(json.loads(rec["body"]))
        except Transient as ex:
            print("transient, will retry", rec.get("messageId"), ex)
            failures.append({"itemIdentifier": rec["messageId"]})
    return {"batchItemFailures": failures}
