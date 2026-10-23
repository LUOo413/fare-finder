import base64, os, urllib.parse
# OrderResultURL: ECPay sends the shopper's browser back with a POST, which a static SPA answers with 405.
# This only redirects; activation happens in flight-ecpay-return.
SITE = os.environ.get("SITE_URL", "https://fare-finder-ruddy.vercel.app")


def handler(event, context):
    raw = event.get("body") or ""
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode()
    p = dict(urllib.parse.parse_qsl(raw, keep_blank_values=True))
    result = "success" if p.get("RtnCode", "1") == "1" else "failed"
    print("browser return", p.get("MerchantTradeNo"), "RtnCode", p.get("RtnCode"), "->", result)
    return {"statusCode": 302, "headers": {"Location": f"{SITE}/app?purchase={result}"}, "body": ""}
