import sys
import logging
import argparse
import datetime
import asyncio
from pulse.bootstrap import bootstrap_secrets

# Bootstrap credentials from environment variables if running in cloud/cron environment
bootstrap_secrets()

from pulse.agent.orchestrator import run_pulse_pipeline
from pulse.ledger.store import get_run, get_deliveries

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("pulse-cli")

def get_default_iso_week() -> str:
    """Returns the previous completed ISO week (e.g. YYYY-Www)."""
    today = datetime.date.today()
    last_week = today - datetime.timedelta(days=7)
    year, week, weekday = last_week.isocalendar()
    return f"{year}-W{week:02d}"

def parse_iso_weeks_range(from_week: str, to_week: str) -> list[str]:
    """Generates all ISO weeks between from_week and to_week inclusive."""
    # Convert week strings to dates representing Monday of that week
    start_date = datetime.datetime.strptime(f"{from_week}-1", "%G-W%V-%u")
    end_date = datetime.datetime.strptime(f"{to_week}-1", "%G-W%V-%u")
    
    weeks = []
    current_date = start_date
    while current_date <= end_date:
        year, week, weekday = current_date.isocalendar()
        weeks.append(f"{year}-W{week:02d}")
        current_date += datetime.timedelta(weeks=1)
        
    return weeks

async def handle_run(args):
    iso_week = args.iso_week or get_default_iso_week()
    logger.info(f"Initiating run for product '{args.product}' and week {iso_week}...")
    res = await run_pulse_pipeline(
        product_name=args.product,
        iso_week=iso_week,
        dry_run=args.dry_run,
        force_send=args.force_send
    )
    
    if res.get("status") == "completed":
        print(f"\nSuccess: Review Pulse completed for week {iso_week}!")
        print(f"Run ID: {res['run_id']}")
        print(f"Reviews processed: {res['reviews_processed']}")
        print(f"Doc URL: {res['doc_url']}\n")
    elif res.get("status") == "skipped":
        print(f"\nSkipped: {res['message']}\n")
    else:
        print(f"\nFailed: {res.get('error')}\n")

async def handle_backfill(args):
    print(f"\nRunning sequential backfill for '{args.product}' from {args.from_week} to {args.to_week}...")
    try:
        weeks = parse_iso_weeks_range(args.from_week, args.to_week)
    except ValueError as e:
        print(f"\nError parsing ISO week format: {e}\n")
        return
        
    print(f"Generating reports for {len(weeks)} weeks: {weeks}\n")
    
    for week in weeks:
        print(f"--- Running week {week} ---")
        res = await run_pulse_pipeline(
            product_name=args.product,
            iso_week=week,
            dry_run=args.dry_run,
            force_send=False
        )
        print(f"Status for {week}: {res.get('status')} - {res.get('message', res.get('error', 'Success'))}\n")
        # Pacing between backfill runs
        await asyncio.sleep(2)

def handle_status(args):
    iso_week = args.iso_week or get_default_iso_week()
    print(f"\nQuerying status for '{args.product}' week {iso_week}...")
    
    run_row = get_run(args.product, iso_week)
    if not run_row:
        print(f"\nNo ledger record found for '{args.product}' week {iso_week}.\n")
        return
        
    run = dict(run_row)
    print(f"\n==========================================")
    print(f"RUN AUDIT: {run['run_id']}")
    print(f"==========================================")
    print(f"Product:         {run['product']}")
    print(f"ISO Week:        {run['iso_week']}")
    print(f"Status:          {run['status'].upper()}")
    print(f"Reviews Count:   {run['review_count']}")
    print(f"Review Window:   {run['window_weeks']} weeks")
    print(f"Started At:      {run['started_at']}")
    print(f"Completed At:    {run['completed_at'] or 'N/A'}")
    if run['error_message']:
        print(f"Error Message:   {run['error_message']}")
        
    deliveries = get_deliveries(run['run_id'])
    if deliveries:
        print(f"\nDeliveries:")
        for idx, deliv in enumerate(deliveries):
            print(f"  {idx + 1}. Channel:      {deliv['channel']}")
            print(f"     External ID:  {deliv['external_id']}")
            if deliv['url']:
                print(f"     URL:          {deliv['url']}")
            if deliv['idempotency_key']:
                print(f"     Idem Key:     {deliv['idempotency_key']}")
    else:
        print("\nNo deliveries logged for this run.")
    print(f"==========================================\n")

def main():
    parser = argparse.ArgumentParser(description="Weekly Product Review Pulse CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")
    
    # 1. run command
    run_parser = subparsers.add_parser("run", help="Run the pulse pipeline for a target week")
    run_parser.add_argument("--product", type=str, default="groww", help="Product name slug (default: groww)")
    run_parser.add_argument("--iso-week", type=str, help="ISO 8601 week to run (e.g. 2026-W24)")
    run_parser.add_argument("--dry-run", action="store_true", help="Skip writes to Google Docs and Gmail")
    run_parser.add_argument("--force-send", action="store_true", help="Ignore run history and send email directly")
    
    # 2. dry-run command
    dry_parser = subparsers.add_parser("dry-run", help="Execute the pipeline in dry-run mode (no API writes)")
    dry_parser.add_argument("--product", type=str, default="groww", help="Product name slug")
    dry_parser.add_argument("--iso-week", type=str, help="ISO 8601 week to run")
    
    # 3. backfill command
    bf_parser = subparsers.add_parser("backfill", help="Run sequential backfills over a range of weeks")
    bf_parser.add_argument("--product", type=str, default="groww", help="Product name slug")
    bf_parser.add_argument("--from-week", type=str, required=True, help="Start week (e.g. 2026-W15)")
    bf_parser.add_argument("--to-week", type=str, required=True, help="End week (e.g. 2026-W24)")
    bf_parser.add_argument("--dry-run", action="store_true", help="Execute backfill in dry-run mode")
    
    # 4. status command
    status_parser = subparsers.add_parser("status", help="Show the audit ledger status of a weekly run")
    status_parser.add_argument("--product", type=str, default="groww", help="Product name slug")
    status_parser.add_argument("--iso-week", type=str, help="ISO 8601 week to check")
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
        
    args = parser.parse_args()
    
    if args.command == "run":
        asyncio.run(handle_run(args))
    elif args.command == "dry-run":
        # Map dry-run args to run handler with dry_run = True
        args.dry_run = True
        args.force_send = False
        asyncio.run(handle_run(args))
    elif args.command == "backfill":
        asyncio.run(handle_backfill(args))
    elif args.command == "status":
        handle_status(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
