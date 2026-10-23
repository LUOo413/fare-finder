import base64, io, zipfile, hashlib, urllib.request, boto3
s3 = boto3.client("s3")
def handler(e, c):
    if e.get("url"):
        src = urllib.request.urlopen(e["url"], timeout=20).read()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            zi = zipfile.ZipInfo("index.py", (2024, 1, 1, 0, 0, 0))
            zi.external_attr, zi.compress_type = 0o644 << 16, zipfile.ZIP_DEFLATED
            z.writestr(zi, src)
        s3.put_object(Bucket=e["bucket"], Key=e["key"], Body=buf.getvalue(), ContentType="application/zip")
        return {"ok": True, "key": e["key"], "src_sha256": hashlib.sha256(src).hexdigest(), "src_bytes": len(src)}
    if e.get("assemble"):
        body = b"".join(s3.get_object(Bucket=e["bucket"], Key=k)["Body"].read() for k in e["parts"])
        s3.put_object(Bucket=e["bucket"], Key=e["key"], Body=body, ContentType=e.get("ct", "application/octet-stream"))
        for k in e["parts"]:
            s3.delete_object(Bucket=e["bucket"], Key=k)
        return {"ok": True, "key": e["key"], "size": len(body)}
    s3.put_object(Bucket=e["bucket"], Key=e["key"], Body=base64.b64decode(e["b64"]), ContentType=e.get("ct", "application/octet-stream"))
    return {"ok": True, "key": e["key"]}
