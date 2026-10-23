import boto3, json, base64, re
from datetime import datetime, timezone
from decimal import Decimal
PLANS = {"tokyo": {"origin": "TPE", "destination": "TYO"}, "seoul": {"origin": "TPE", "destination": "SEL"}, "london": {"origin": "TPE", "destination": "LON"}}
ddb = boto3.resource("dynamodb").Table("subscriptions")
H = {"Content-Type": "application/json"}
def resp(code, obj):
    return {"statusCode": code, "headers": H, "body": json.dumps(obj, ensure_ascii=False)}
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
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
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
    now = datetime.now(timezone.utc).isoformat()
    ddb.update_item(
        Key={"email": email, "route": route},
        UpdateExpression="SET #pn=:p, #o=:o, #d=:d, #tp=:t, #c=:c, #u=:u, #ca=if_not_exists(#ca,:u)",
        ExpressionAttributeNames={"#pn": "plan_name", "#o": "origin", "#d": "destination", "#tp": "target_price", "#c": "currency", "#u": "updated_at", "#ca": "created_at"},
        ExpressionAttributeValues={":p": plan, ":o": p["origin"], ":d": p["destination"], ":t": tp, ":c": "TWD", ":u": now})
    return resp(200, {"ok": True, "email": email, "route": route, "plan_name": plan, "target_price": int(tp) if tp == tp.to_integral() else float(tp), "currency": "TWD"})
