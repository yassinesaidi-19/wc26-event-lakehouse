CREATE OR REPLACE VIEW wc26_lakehouse.quality.latest_quality_status AS
SELECT status, summary, row_counts
FROM wc26_lakehouse.quality.quality_report;

CREATE OR REPLACE VIEW wc26_lakehouse.quality.source_contribution_summary AS
SELECT *
FROM wc26_lakehouse.quality.source_contribution_report;

CREATE OR REPLACE VIEW wc26_lakehouse.marts.tournament_summary AS
SELECT
  tournament_id,
  competition_year,
  COUNT(*) AS standings_rows,
  COUNT(DISTINCT group_id) AS groups_generated,
  COUNT(DISTINCT team_id) AS teams_in_state
FROM wc26_lakehouse.state.state_group_standings
GROUP BY tournament_id, competition_year;
