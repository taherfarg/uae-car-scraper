import asyncio
import argparse
import json
import logging
import os
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/run_{datetime.now().strftime('%Y%m%d_%H%M')}.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("runner")


def ensure_dirs():
    """Create required directories."""
    for d in ["data/raw", "data/processed", "output", "logs"]:
        os.makedirs(d, exist_ok=True)


async def cmd_scrape(args):
    """Run scrapers."""
    ensure_dirs()
    results = {"dubizzle": [], "dubicars": []}

    if args.source in ("all", "dubizzle"):
        from dubizzle_spider import EnhancedDubizzleSpider
        logger.info("=== Starting Dubizzle Scraper ===")
        spider = EnhancedDubizzleSpider(
            max_pages=args.pages,
            min_delay=args.min_delay,
            max_delay=args.max_delay,
        )
        results["dubizzle"] = await spider.scrape_all()
        # Save raw data
        with open("data/raw/dubizzle_raw.json", "w", encoding="utf-8") as f:
            json.dump(results["dubizzle"], f, indent=2, default=str)
        logger.info(f"Dubizzle: {len(results['dubizzle'])} listings saved")

    if args.source in ("all", "dubicars"):
        from dubicars_spider import EnhancedDubicarsSpider
        logger.info("=== Starting Dubicars Scraper ===")
        spider = EnhancedDubicarsSpider(
            max_pages=args.pages,
            scrape_details=args.details,
            min_delay=args.min_delay,
            max_delay=args.max_delay,
        )
        results["dubicars"] = await spider.scrape_all()
        with open("data/raw/dubicars_raw.json", "w", encoding="utf-8") as f:
            json.dump(results["dubicars"], f, indent=2, default=str)
        logger.info(f"Dubicars: {len(results['dubicars'])} listings saved")

    total = len(results["dubizzle"]) + len(results["dubicars"])
    logger.info(f"=== Scraping Complete: {total} total listings ===")
    return results


def cmd_process(args):
    """Process and merge raw data."""
    from process_and_merge import EnhancedProcessor

    ensure_dirs()

    # Load raw data
    dubizzle_data = []
    dubicars_data = []

    try:
        with open("data/raw/dubizzle_raw.json") as f:
            dubizzle_data = json.load(f)
    except FileNotFoundError:
        logger.warning("No Dubizzle raw data found")

    try:
        with open("data/raw/dubicars_raw.json") as f:
            dubicars_data = json.load(f)
    except FileNotFoundError:
        logger.warning("No Dubicars raw data found")

    if not dubizzle_data and not dubicars_data:
        logger.error("No raw data found. Run 'scrape' first.")
        return None

    processor = EnhancedProcessor(dubizzle_data, dubicars_data)
    df = processor.run_pipeline()

    # Export
    processor.export_to_csv("data/processed/listings.csv")
    processor.export_to_json("data/processed/listings.json")

    if args.excel:
        processor.export_to_excel("output/uae_car_market.xlsx")

    # Save quality report
    with open("data/processed/quality_report.json", "w") as f:
        json.dump(processor.quality_report, f, indent=2, default=str)

    return df


def cmd_analyze(args):
    """Run analysis and generate dashboard."""
    from analyze_and_dashboard import EnhancedAnalyzer
    import pandas as pd

    try:
        df = pd.read_csv("data/processed/listings.csv")
    except FileNotFoundError:
        logger.error("No processed data found. Run 'process' first.")
        return

    analyzer = EnhancedAnalyzer(df)
    output = args.output or "output/dashboard.html"
    analyzer.generate_dashboard(output)
    logger.info(f"Dashboard ready: {output}")

    # Also export insights JSON
    insights = analyzer.insights
    with open("output/insights.json", "w") as f:
        json.dump(insights, f, indent=2, default=str)


async def cmd_all(args):
    """Run the complete pipeline."""
    logger.info("╔══════════════════════════════════════╗")
    logger.info("║  UAE Car Market — Full Pipeline      ║")
    logger.info("╚══════════════════════════════════════╝")

    # Step 1: Scrape
    logger.info("\n📥 STEP 1/3: Scraping...")
    await cmd_scrape(args)

    # Step 2: Process
    logger.info("\n🧠 STEP 2/3: Processing & Enrichment...")
    args.excel = True
    cmd_process(args)

    # Step 3: Analyze & Dashboard
    logger.info("\n📊 STEP 3/3: Analysis & Dashboard...")
    cmd_analyze(args)

    logger.info("\n✅ Pipeline complete! Check the 'output/' folder.")


def cmd_serve(args):
    """Start the web UI server."""
    import uvicorn
    from app.database import init_database

    # Auto-init DB if needed
    if not os.path.exists("data/cars.db"):
        print("[*] Initializing database...")
        try:
            count = init_database()
            print(f"[OK] Loaded {count} listings into database")
        except FileNotFoundError:
            print("[!] No processed data found. Run 'python run.py process' first.")
            return

    print(f"\n[*] Starting UAE Car Market Search UI...")
    print(f"    Open http://localhost:{args.port} in your browser\n")

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


def main():
    parser = argparse.ArgumentParser(
        description="🇦🇪 UAE Car Market Scraper & Intelligence Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py scrape --source all --pages 30
  python run.py scrape --source dubizzle --pages 50
  python run.py process --excel
  python run.py analyze --output my_dashboard.html
  python run.py all --pages 25 --details
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape car listings")
    scrape_parser.add_argument("--source", choices=["all", "dubizzle", "dubicars"], default="all")
    scrape_parser.add_argument("--pages", type=int, default=30, help="Max pages to scrape per source")
    scrape_parser.add_argument("--min-delay", type=float, default=2, help="Min delay between requests (s)")
    scrape_parser.add_argument("--max-delay", type=float, default=5, help="Max delay between requests (s)")
    scrape_parser.add_argument("--details", action="store_true", help="Scrape individual listing pages for richer data")

    # Process command
    process_parser = subparsers.add_parser("process", help="Process & merge raw data")
    process_parser.add_argument("--excel", action="store_true", help="Also export to Excel")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze data & generate dashboard")
    analyze_parser.add_argument("--output", type=str, default="output/dashboard.html")

    # Full pipeline
    all_parser = subparsers.add_parser("all", help="Run complete pipeline (scrape → process → analyze)")
    all_parser.add_argument("--source", choices=["all", "dubizzle", "dubicars"], default="all")
    all_parser.add_argument("--pages", type=int, default=30)
    all_parser.add_argument("--min-delay", type=float, default=2)
    all_parser.add_argument("--max-delay", type=float, default=5)
    all_parser.add_argument("--details", action="store_true")
    all_parser.add_argument("--output", type=str, default="output/dashboard.html")

    # Serve web UI
    serve_parser = subparsers.add_parser("serve", help="Start the web search UI")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port number")
    serve_parser.add_argument("--reload", action="store_true", help="Auto-reload on changes")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "scrape":
        asyncio.run(cmd_scrape(args))
    elif args.command == "process":
        cmd_process(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "all":
        asyncio.run(cmd_all(args))
    elif args.command == "serve":
        cmd_serve(args)


if __name__ == "__main__":
    main()
