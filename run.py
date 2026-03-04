"""
UAE Car Market Scraper — Unified CLI Runner
Usage:
    python run.py process    — Process & merge raw JSON data into enriched CSV
    python run.py analyze    — Generate interactive HTML dashboard from CSV
    python run.py all        — Run process + analyze in sequence
    python run.py export     — Export to Excel format
"""

import argparse
import sys
import os


def cmd_process():
    """Run the data processing pipeline."""
    from process_and_merge import main as process_main
    process_main()


def cmd_analyze():
    """Generate the analytics dashboard."""
    from analyze_and_dashboard import generate_dashboard
    generate_dashboard()


def cmd_export(fmt="xlsx"):
    """Export data to additional formats."""
    import pandas as pd
    
    csv_path = "uae_cars_market_data.csv"
    if not os.path.exists(csv_path):
        print(f"❌ {csv_path} not found. Run 'python run.py process' first.")
        return
    
    df = pd.read_csv(csv_path)
    
    if fmt == "xlsx":
        try:
            output = "uae_cars_market_data.xlsx"
            df.to_excel(output, index=False, sheet_name="Market Data")
            print(f"✅ Exported to {output}")
        except ImportError:
            print("❌ openpyxl not installed. Run: pip install openpyxl")
    elif fmt == "json":
        output = "uae_cars_market_data_processed.json"
        df.to_json(output, orient="records", indent=2)
        print(f"✅ Exported to {output}")
    else:
        print(f"❌ Unknown format: {fmt}. Supported: xlsx, json")


def cmd_all():
    """Run the full pipeline."""
    print("\n" + "=" * 60)
    print("  STEP 1: Processing & Merging Data")
    print("=" * 60)
    cmd_process()
    
    print("\n" + "=" * 60)
    print("  STEP 2: Generating Analytics Dashboard")
    print("=" * 60)
    cmd_analyze()
    
    print("\n" + "=" * 60)
    print("  🎉 All done! Open dashboard.html in your browser.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="UAE Car Market Scraper — CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  process   Process raw JSON files into enriched CSV
  analyze   Generate interactive HTML dashboard
  all       Run process + analyze
  export    Export to Excel/JSON (use --format xlsx or json)

Examples:
  python run.py all
  python run.py process
  python run.py analyze
  python run.py export --format xlsx
        """
    )
    
    parser.add_argument("command", choices=["process", "analyze", "all", "export"],
                        help="Command to run")
    parser.add_argument("--format", default="xlsx", choices=["xlsx", "json"],
                        help="Export format (for 'export' command)")
    
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    args = parser.parse_args()
    
    commands = {
        "process": cmd_process,
        "analyze": cmd_analyze,
        "all": cmd_all,
        "export": lambda: cmd_export(args.format),
    }
    
    commands[args.command]()


if __name__ == "__main__":
    main()
