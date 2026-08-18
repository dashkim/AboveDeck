#!/usr/bin/env python3
"""Keep Neon slim: peaks + upcoming predictions only.

Training tables (weather_peak, observations) are truncated.
Predictions older than now, or further than --horizon-days ahead, are deleted.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.db import execute


def run(*, horizon_days: int = 7) -> None:
    execute("TRUNCATE weather_peak, observations RESTART IDENTITY")
    execute(
        """
        DELETE FROM predictions
        WHERE valid_at < now()
           OR valid_at >= now() + make_interval(days => %s)
        """,
        (horizon_days,),
    )
    print(
        f"Cleared weather_peak and observations; "
        f"kept predictions from now through +{horizon_days} days."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Prune Neon to peaks + upcoming predictions")
    parser.add_argument(
        "--horizon-days",
        type=int,
        default=7,
        help="Keep predictions this many days ahead (default 7)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Deprecated alias for --horizon-days",
    )
    args = parser.parse_args()
    run(horizon_days=args.days if args.days is not None else args.horizon_days)


if __name__ == "__main__":
    main()
