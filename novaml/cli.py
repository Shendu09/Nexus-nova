"""CLI interface for novaml."""

from __future__ import annotations
import argparse
import sys
import json
import logging
from pathlib import Path
import novaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def format_output(data: dict, output_format: str) -> str:
    """Format output as JSON or pretty-printed."""
    if output_format == "json":
        return json.dumps(data, indent=2, default=str)
    else:
        return str(data)


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="novaml - AI-powered log intelligence")
    parser.add_argument("--version", action="version", version=f"novaml {novaml.__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Subcommand")

    # Triage subcommand
    triage_parser = subparsers.add_parser("triage", help="Full log triage")
    triage_parser.add_argument("--file", help="Log file to analyze")
    triage_parser.add_argument("--model", default="mistral", help="LLM model name")
    triage_parser.add_argument("--output", choices=["text", "json"], default="text")

    # Detect subcommand
    detect_parser = subparsers.add_parser("detect", help="Anomaly detection")
    detect_parser.add_argument("--file", help="Log file")
    detect_parser.add_argument("--output", choices=["text", "json"], default="text")

    # Train subcommand
    train_parser = subparsers.add_parser("train", help="Train on own logs")
    train_parser.add_argument("--log-file", required=True, help="Training log file")
    train_parser.add_argument("--save-dir", default="~/.novaml/models", help="Model save directory")
    train_parser.add_argument("--output", choices=["text", "json"], default="text")

    # Serve subcommand
    serve_parser = subparsers.add_parser("serve", help="Start REST API server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Server host")
    serve_parser.add_argument("--port", type=int, default=8000, help="Server port")

    # Version subcommand
    subparsers.add_parser("version", help="Show version")

    args = parser.parse_args()

    try:
        if args.command == "version":
            print(f"novaml {novaml.__version__}")
            return 0

        elif args.command == "triage":
            logs = []
            if args.file:
                with open(args.file) as f:
                    logs = f.readlines()
            else:
                logs = sys.stdin.readlines()

            result = novaml.triage(logs, model=args.model)
            if args.output == "json":
                print(json.dumps(result.to_dict(), indent=2, default=str))
            else:
                print(result)
            return 0

        elif args.command == "detect":
            logs = []
            if args.file:
                with open(args.file) as f:
                    logs = f.readlines()
            else:
                logs = sys.stdin.readlines()

            result = novaml.detect(logs)
            if args.output == "json":
                print(json.dumps(
                    {
                        "scores": result.scores,
                        "anomalous_indices": result.anomalous_indices,
                        "threshold": result.threshold,
                        "method": result.method,
                    },
                    default=str
                ))
            else:
                print(result)
            return 0

        elif args.command == "train":
            with open(args.log_file) as f:
                logs = f.readlines()

            stats = novaml.train(logs, save_dir=args.save_dir)
            print(format_output(stats, args.output))
            return 0

        elif args.command == "serve":
            novaml.serve(host=args.host, port=args.port)
            return 0

        else:
            parser.print_help()
            return 1

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
