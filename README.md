# Demand Radar

Demand Radar finds app ideas and concepts that people want right now. It pulls public signals, groups them into concepts and ranks the concepts by demand.

It uses only the Python standard library (3.10+), and none of the default sources need an API key.

```bash
python -m demand_radar                       # all sources, last 30 days, Markdown to stdout
python -m demand_radar --days 7 --out report.md --json report.json
python -m demand_radar --sources hackernews,reddit --top 30
python -m demand_radar --save-signals raw.json      # keep raw data for history or replay
python -m demand_radar --from-signals raw.json      # re-analyze without fetching
```

## How it works

```
sources ──► signals ──► concepts ──► scores ──► report
```

1. **Collect signals** (`demand_radar/sources/`). Each signal is a post, repo, launch or chart entry with an engagement number:

   | Source | What it captures | Engagement |
   |---|---|---|
   | Hacker News (Algolia API) | Show HN launches, "Ask HN: is there a tool…", "alternative to…" | points + comments |
   | Reddit (public JSON) | r/SomebodyMakeThis, r/AppIdeas, r/SideProject, r/SaaS, …, plus site-wide "is there an app" searches | upvotes + comments |
   | GitHub search | the most-starred repos created inside the window | stars + forks |
   | App Store top charts | what consumers are downloading right now (top free and top paid) | chart rank |
   | Product Hunt feed | recent launches | none (counts toward volume) |

2. **Map signals to concepts** (`extract.py`) in two ways:
   - **Taxonomy:** about 45 app categories in `taxonomy.json`, each defined by keyword phrases. You can edit the file or pass your own with `--taxonomy`.
   - **Emerging phrases:** 2–3 word phrases that recur across titles. These catch niches the taxonomy doesn't name yet.

3. **Detect explicit demand.** Phrases such as "is there an app", "I'd pay for", "wish someone would build" and "alternative to" mark a signal as an **ask**. An ask shows an unmet need, which is a stronger signal than general popularity.

4. **Score** (`scoring.py`). Each concept gets five components. Each component is converted to a percentile across all concepts, so HN points, GitHub stars and chart ranks can be compared. The weighted blend becomes a 0–100 score.

   | Component | Weight | Meaning |
   |---|---:|---|
   | engagement | 0.30 | log-damped attention on matching signals |
   | intent | 0.25 | number of explicit asks |
   | momentum | 0.20 | activity in the recent half of the window vs the older half |
   | volume | 0.15 | number of distinct signals |
   | diversity | 0.10 | number of independent sources that agree |

5. **Report** (`report.py`). The Markdown report has a ranked concept table, evidence links for each concept, emerging phrases and the top unmet asks. With `--json` it also writes the same data as JSON.

## Tips

- Run it on a schedule with `--save-signals` so you build up a history.
- To go deeper on one domain, point `--taxonomy` at a file of narrow sub-concepts (for example, only fitness app types).
- Set `GITHUB_TOKEN` to raise GitHub's rate limit.
- Reddit rate-limits anonymous clients. If it fails, run it again later or pass `--sources` without it. A failing source is skipped; it doesn't stop the run.

## Tests

```bash
python -m unittest discover -s tests
```
