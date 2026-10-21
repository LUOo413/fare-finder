import boto3, json, re
from decimal import Decimal
from boto3.dynamodb.conditions import Key
ddb = boto3.resource("dynamodb").Table("subscriptions")
H = {"Content-Type": "application/json"}
def conv(v):
    if isinstance(v, Decimal):
        return int(v) if v == v.to_integral() else float(v)
    return v
def handler(event, context):
    email = ((event.get("queryStringParameters") or {}).get("email") or "").strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return {"statusCode": 400, "headers": H, "body": json.dumps({"error": "invalid email"})}
    items = ddb.query(KeyConditionExpression=Key("email").eq(email))["Items"]
    out = [{k: conv(v) for k, v in it.items()} for it in items]
    return {"statusCode": 200, "headers": H, "body": json.dumps({"subscriptions": out}, ensure_ascii=False)}
