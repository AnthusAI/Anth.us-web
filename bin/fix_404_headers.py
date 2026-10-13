#!/usr/bin/env python3
"""Give the stored 404 page the headers the previous host sent with it: ``text/html`` and no ``Cache-Control``.

CloudFront serves the 404 page through a custom error response, and a viewer-response function does not run
for it, so the headers come from the stored object. Run after a ``project --all`` (which writes the page with
the projection's default headers).

Usage: fix_404_headers.py BUCKET
"""

import sys

import boto3

KEY = "404.html"


def main(bucket):
    s3 = boto3.client("s3")
    head = s3.head_object(Bucket=bucket, Key=KEY)
    s3.copy_object(
        Bucket=bucket,
        Key=KEY,
        CopySource={"Bucket": bucket, "Key": KEY},
        MetadataDirective="REPLACE",
        ContentType="text/html",
        Metadata=head.get("Metadata", {}),
    )


if __name__ == "__main__":
    main(sys.argv[1])
