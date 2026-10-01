"""box2.receiver — the application's webhook handlers and AWS Lambda entry point.

The webhook receiver framework (``create_app``, ``WebhookRoute``, ``ReceiverConfig``,
deduplication, ...) lives in ``gds_idea_sharepoint.receiver``. This package holds only what
is specific to this application:

- ``route_handlers`` — the triage, QA and action-extraction handlers.
- ``lambda_handler`` — wires the routes to SharePoint and exposes the Mangum ``handler``.
"""
