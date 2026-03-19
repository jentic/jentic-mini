#!/usr/bin/env python3
"""Seed api_broker_apps table — maps known API IDs to their Pipedream broker_app_id.

Run once after migration; safe to re-run (upsert).

Usage:
    python scripts/seed_api_broker_apps.py [--broker-id pipedream] [--dry-run]
"""
import asyncio
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import aiosqlite

DB_PATH = os.getenv("DB_PATH", "/app/data/jentic-mini.db")

# Maps our api_id (hostname-derived) → Pipedream app slug.
# Add new entries here as APIs are onboarded.
PIPEDREAM_APP_SEEDS: dict[str, str] = {
    # Google
    "gmail.googleapis.com":            "gmail",
    "www.googleapis.com":              "gmail",           # legacy Gmail API host
    "calendar.googleapis.com":         "google_calendar",
    "people.googleapis.com":           "google_people",
    "sheets.googleapis.com":           "google_sheets",
    "docs.googleapis.com":             "google_docs",
    "drive.googleapis.com":            "google_drive",
    "slides.googleapis.com":           "google_slides",
    "oauth2.googleapis.com":           "google",
    "admin.googleapis.com":            "google_admin",
    # GitHub
    "api.github.com":                  "github",
    # Slack
    "slack.com":                       "slack",
    "api.slack.com":                   "slack",
    # Stripe
    "api.stripe.com":                  "stripe",
    # Twilio
    "api.twilio.com":                  "twilio",
    # HubSpot
    "api.hubapi.com":                  "hubspot",
    # Salesforce
    "salesforce.com":                  "salesforce_rest_api",
    # Intercom
    "api.intercom.io":                 "intercom",
    # Notion
    "api.notion.com":                  "notion",
    # Airtable
    "api.airtable.com":                "airtable",
    # Jira / Atlassian
    "api.atlassian.com":               "jira",
    "atlassian.net":                   "jira",
    # Linear
    "api.linear.app":                  "linear_app",
    # Discord
    "discord.com/api":                 "discord",
    "discord.com":                     "discord",
    # Zoom
    "api.zoom.us":                     "zoom",
    # Shopify
    "myshopify.com":                   "shopify",
    # Xero
    "api.xero.com":                    "xero",
    # Dropbox
    "api.dropboxapi.com":              "dropbox",
    # Box
    "api.box.com":                     "box",
    # Twitter / X
    "api.twitter.com":                 "twitter",
    "api.x.com":                       "twitter",
    # LinkedIn
    "api.linkedin.com":                "linkedin",
    # Asana
    "app.asana.com/api":               "asana",
    # Trello
    "api.trello.com":                  "trello",
    # Monday.com
    "api.monday.com":                  "monday",
    # Pipedrive
    "api.pipedrive.com":               "pipedrive",
    # Zendesk
    "zendesk.com":                     "zendesk",
    # Freshdesk
    "freshdesk.com":                   "freshdesk",
    # SendGrid
    "api.sendgrid.com":                "sendgrid",
    # Mailchimp
    "api.mailchimp.com":               "mailchimp",
    # Spotify
    "api.spotify.com":                 "spotify",
    # Typeform
    "api.typeform.com":                "typeform",
    # OpenAI
    "api.openai.com":                  "openai",
    # Anthropic (not in Pipedream as of seed date, include for future)
    # "api.anthropic.com":             "anthropic",
}


async def seed(broker_id: str, dry_run: bool) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        # Verify broker exists
        async with db.execute("SELECT id FROM oauth_brokers WHERE id=?", (broker_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            print(f"⚠️  Broker '{broker_id}' not found in oauth_brokers — skipping seed.")
            print("   Create the broker first via POST /oauth-brokers, then re-run.")
            return

        # Fetch all local api_ids for matching
        async with db.execute("SELECT id FROM apis") as cur:
            local_api_ids = {r[0] for r in await cur.fetchall()}

        inserted = updated = skipped_no_api = skipped_no_match = 0

        for api_id, broker_app_id in PIPEDREAM_APP_SEEDS.items():
            if api_id not in local_api_ids:
                skipped_no_api += 1
                continue

            # Check existing
            async with db.execute(
                "SELECT broker_app_id FROM api_broker_apps WHERE api_id=? AND broker_id=?",
                (api_id, broker_id),
            ) as cur:
                existing = await cur.fetchone()

            if existing:
                if existing[0] == broker_app_id:
                    skipped_no_match += 1
                    continue
                action = "UPDATE"
                updated += 1
            else:
                action = "INSERT"
                inserted += 1

            print(f"  {action}: {api_id} → {broker_app_id}")
            if not dry_run:
                await db.execute(
                    """INSERT INTO api_broker_apps (api_id, broker_id, broker_app_id)
                       VALUES (?, ?, ?)
                       ON CONFLICT(api_id, broker_id) DO UPDATE SET broker_app_id=excluded.broker_app_id""",
                    (api_id, broker_id, broker_app_id),
                )

        if not dry_run:
            await db.commit()

        print(f"\n{'[DRY RUN] ' if dry_run else ''}Done: {inserted} inserted, {updated} updated, "
              f"{skipped_no_match} unchanged, {skipped_no_api} skipped (api not in local DB)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker-id", default="pipedream", help="oauth_brokers.id to seed against")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    asyncio.run(seed(args.broker_id, args.dry_run))


if __name__ == "__main__":
    main()
