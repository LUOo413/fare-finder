import base64, boto3
s3 = boto3.client("s3")
def handler(e, c):
    if e.get("assemble"):
        body = b"".join(s3.get_object(Bucket=e["bucket"], Key=k)["Body"].read() for k in e["parts"])
        s3.put_object(Bucket=e["bucket"], Key=e["key"], Body=body, ContentType=e.get("ct", "application/octet-stream"))
        for k in e["parts"]:
            s3.delete_object(Bucket=e["bucket"], Key=k)
        return {"ok": True, "key": e["key"], "size": len(body)}
    s3.put_object(Bucket=e["bucket"], Key=e["key"], Body=base64.b64decode(e["b64"]), ContentType=e.get("ct", "application/octet-stream"))
    return {"ok": True, "key": e["key"]}
