"""Local runner for the file triage pipeline.

Runs triage_file() on a local file and prints the structured result as
JSON. Requires AWS credentials for Bedrock (the LLM calls).

Usage:
    AWS_PROFILE=bedrock-dev uv run python examples/triage/local_pipeline.py <file_path>

Example:
    AWS_PROFILE=bedrock-dev uv run python examples/triage/local_pipeline.py examples/data/example_test.txt
"""

import asyncio
import json
import logging
import sys

from box2.pipeline import triage_file


async def main() -> None:
    """Run the triage pipeline on a file and print the result."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if len(sys.argv) < 2:
        print("Usage: uv run python examples/triage/local_pipeline.py <file_path>")
        print("\nExample:")
        print("  AWS_PROFILE=bedrock-dev uv run python examples/triage/local_pipeline.py examples/data/example_test.txt")
        sys.exit(1)

    file_path = sys.argv[1]
    print(f"\nRunning triage pipeline on: {file_path}\n")

    result = await triage_file(file_path)

    print("\n" + "=" * 80)
    print("TRIAGE RESULT")
    print("=" * 80)
    print(json.dumps(result.model_dump(mode="json"), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
