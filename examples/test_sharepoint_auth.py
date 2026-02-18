"""Test SharePoint authentication.

Verifies the full auth chain:
  AWS STS JWT → Azure AD token exchange → Microsoft Graph API call

Set these environment variables before running:
    export AWS_PROFILE=<your-profile>
    export SHAREPOINT_TENANT_ID=<azure-ad-tenant-id>
    export SHAREPOINT_CLIENT_ID=<azure-ad-client-id>
    export SHAREPOINT_SITE_ID=<sharepoint-site-id>

Usage:
    uv run python examples/test_sharepoint_auth.py
"""

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    from box2.sharepoint import SharePointSession

    # Step 1: Create session from environment variables
    logger.info("Creating SharePoint session from environment variables...")
    try:
        session = SharePointSession.from_env()
        logger.info("Session created (tenant=%s, site=%s)", session.tenant_id, session.site_id)
    except Exception as e:
        logger.error("Failed to create session: %s", e)
        sys.exit(1)

    # Step 2: Get a Graph API token
    logger.info("Acquiring Microsoft Graph token...")
    try:
        token = session.get_token()
        # Show first/last few chars only — don't log the full token
        logger.info("Token acquired: %s...%s", token[:10], token[-10:])
    except Exception as e:
        logger.error("Failed to acquire token: %s", e)
        sys.exit(1)

    # Step 3: Make a test API call — get site info
    logger.info("Testing Graph API call: GET /sites/%s ...", session.site_id)
    try:
        response = session._http.get(
            f"/sites/{session.site_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        site = response.json()
        logger.info("Site name: %s", site.get("displayName", "unknown"))
        logger.info("Site URL: %s", site.get("webUrl", "unknown"))
        logger.info("Authentication successful!")
    except Exception as e:
        logger.error("Graph API call failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
