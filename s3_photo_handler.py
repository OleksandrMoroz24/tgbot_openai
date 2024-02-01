import mimetypes
import os
from io import BytesIO

import boto3
from botocore.exceptions import NoCredentialsError


async def upload_to_s3(file_path, file_content):
    bucket_name = os.getenv("AWS_S3_BUCKET_NAME")
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_S3_REGION_NAME"),
    )

    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = "application/octet-stream"

    fileobj = BytesIO(file_content)
    try:
        s3.upload_fileobj(
            Fileobj=fileobj,
            Bucket=bucket_name,
            Key=file_path,
            ExtraArgs={"ContentType": content_type},
        )
        file_url = f"https://{bucket_name}.s3.amazonaws.com/{file_path}"
        return file_url
    except NoCredentialsError:
        print("AWS credentials are not available")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
