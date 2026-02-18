import os

import boto3
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.providers.bedrock import BedrockProvider

# Model IDs
SONNET_45 = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
HAIKU_45 = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"

# Configuration from environment variables with defaults
AWS_REGION = os.getenv("AWS_REGION", "eu-west-2")
MODEL_ID = os.getenv("CLAUDE_MODEL", SONNET_45)
MINISTER_PERSONA_PATH = os.getenv("MINISTER_PERSONA_PATH", "data/example_science_minister.json")

session = boto3.Session(
    region_name=AWS_REGION,
    profile_name=os.getenv("AWS_PROFILE"),
)

bedrock_client = session.client("bedrock-runtime")

model = BedrockConverseModel(MODEL_ID, provider=BedrockProvider(bedrock_client=bedrock_client))
