"""Object Storage (S3-compatible, Vultr Object Storage) access for the worker.

Env:
  S3_ENDPOINT    e.g. https://ewr1.vultrobjects.com
  S3_REGION      default us-east-1 (Vultr ignores it, boto3 needs one)
  S3_BUCKET      the private bucket (photos/<job>/..., builds/<job>/...)
  S3_ACCESS_KEY, S3_SECRET_KEY
  STORAGE_DIR    use a local directory instead of S3 (dev / tests)
"""
import mimetypes
import os
import shutil


class S3Storage:
    def __init__(self, bucket, endpoint=None, region="us-east-1", access_key=None, secret_key=None, client=None):
        if client is None:
            import boto3
            from botocore.config import Config
            client = boto3.client("s3", endpoint_url=endpoint, region_name=region, aws_access_key_id=access_key,
                                  aws_secret_access_key=secret_key,
                                  config=Config(signature_version="s3v4", retries={"max_attempts": 5}))
        self.s3 = client
        self.bucket = bucket

    def list(self, prefix):
        keys = []
        for page in self.s3.get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=prefix):
            keys.extend(o["Key"] for o in page.get("Contents", []))
        return sorted(keys)

    def get(self, key):
        return self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def put_file(self, key, path):
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        if path.endswith((".c", ".h")):
            ctype = "text/plain"
        elif path.endswith(".glb"):
            ctype = "model/gltf-binary"
        self.s3.upload_file(path, self.bucket, key, ExtraArgs={"ContentType": ctype})

    def delete_prefix(self, prefix):
        keys = self.list(prefix)
        for i in range(0, len(keys), 1000):
            result = self.s3.delete_objects(Bucket=self.bucket,
                                            Delete={"Objects": [{"Key": k} for k in keys[i:i + 1000]], "Quiet": True})
            if result.get("Errors"):
                raise OSError("Object storage rejected one or more deletions")
        return len(keys)


class LocalStorage:
    """Same interface on a directory (keys are relative paths)."""

    def __init__(self, root):
        self.root = os.path.abspath(root)

    def _p(self, key):
        p = os.path.abspath(os.path.join(self.root, key))
        if not p.startswith(self.root + os.sep):
            raise ValueError(f"bad key {key!r}")
        return p

    def list(self, prefix):
        out = []
        for dirpath, _dirs, files in os.walk(self.root):
            for f in files:
                key = os.path.relpath(os.path.join(dirpath, f), self.root).replace(os.sep, "/")
                if key.startswith(prefix):
                    out.append(key)
        return sorted(out)

    def get(self, key):
        with open(self._p(key), "rb") as f:
            return f.read()

    def put_file(self, key, path):
        dst = self._p(key)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(path, dst)

    def delete_prefix(self, prefix):
        keys = self.list(prefix)
        for k in keys:
            os.remove(self._p(k))
        return len(keys)


def from_env():
    if os.environ.get("STORAGE_DIR"):
        return LocalStorage(os.environ["STORAGE_DIR"])
    return S3Storage(os.environ["S3_BUCKET"], os.environ.get("S3_ENDPOINT"), os.environ.get("S3_REGION", "us-east-1"),
                     os.environ.get("S3_ACCESS_KEY"), os.environ.get("S3_SECRET_KEY"))
