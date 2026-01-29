import os

import boto3

SONNET_45 = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
HAIKU_45 = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"

AWS_REGION = "eu-west-2"


session = boto3.Session(
    region_name=AWS_REGION,
    profile_name=os.getenv("AWS_PROFILE"),
)

bedrock_client = session.client("bedrock-runtime")
