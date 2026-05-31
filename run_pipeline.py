"""Top-level command for the local MVP tournament lakehouse."""

from __future__ import annotations

from wc2026.io_utils import read_csv
from wc2026.pipeline import run_pipeline
from wc2026.paths import QUALITY_DIR


def main() -> None:
    result = run_pipeline(include_api=True)
    print("Pipeline completed.")
    for message in result["api_messages"]:
        print(message)
    summary = result["pipeline_summary"]
    print("Final pipeline summary:")
    print(f"events created: {summary['events_created']}")
    print(f"teams: {summary['teams']}")
    print(f"matches: {summary['matches']}")
    print(f"match events: {summary['match_events']}")
    print(f"tournaments found: {summary['tournaments_found']}")
    print(f"finished group-stage matches used: {summary['finished_group_stage_matches_used']}")
    print(f"standings rows: {summary['standings_rows']}")
    print(f"groups generated: {summary['groups_generated']}")
    print(f"quality checks passed: {summary['quality_checks_passed']}")
    print(f"quality checks failed: {summary['quality_checks_failed']}")
    contribution_path = QUALITY_DIR / "source_contribution_report.csv"
    if contribution_path.exists():
        print("Source contribution report:")
        contribution = read_csv(contribution_path)
        for _, row in contribution.iterrows():
            print(
                f"{row['source_name']}: teams={int(row['teams_count'])}, matches={int(row['matches_count'])}, "
                f"match_events={int(row['match_events_count'])}, event_log={int(row['event_log_count'])}"
            )


if __name__ == "__main__":
    main()
