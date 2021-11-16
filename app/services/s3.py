from io import StringIO

import boto3
from botocore.config import Config
from django.conf import settings


BOTO_SETTINGS = {
    "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
    "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
    "region_name": settings.AWS_REGION,
}

BOTO_SETTINGS_v4 = dict(config=Config(signature_version="s3v4"), **BOTO_SETTINGS)

_session = None


def get_session():
    if _session:
        return _session
    return boto3.Session(**BOTO_SETTINGS)


def get_s3_client():
    return get_session().client("s3")


def get_s3_clientv4():
    return boto3.client("s3", **BOTO_SETTINGS_v4)


def download_file(file_key):
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    file_object = StringIO()
    get_s3_client().download_fileobj(bucket_name, file_key, file_object)
    file_object.seek(0)

    return file_object


def generate_presigned_post(file_path, expires_in=300):
    s3_upload_data = get_s3_clientv4().generate_presigned_post(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=file_path, ExpiresIn=expires_in
    )
    return s3_upload_data
