# Demand Radar

Demand Radar finds app ideas and concepts that people want right now. It pulls public signals, groups them into concepts and ranks the concepts by demand.

It uses only the Python standard library (3.9+), and none of the default sources need an API key.

Run all commands from this folder (`cd demand-radar`).

```bash
python3 -m demand_radar                       # all sources, last 30 days, Markdown to stdout
python3 -m demand_radar --days 7 --out report.md --json report.json
python3 -m demand_radar --sources hackernews,reddit --top 30
python3 -m demand_radar --save-signals raw.json      # keep raw data for history or replay
python3 -m demand_radar --from-signals raw.json      # re-analyze without fetching
python3 -m demand_radar --cluster sbert              # true sentence embeddings (pip install sentence-transformers)
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
   | Google Trends | trending searches, plus search-interest growth for each concept | approx. search volume; growth feeds the **search** component |

2. **Map signals to concepts** (`extract.py`) in two ways:
   - **Taxonomy:** about 45 app categories in `taxonomy.json`, each defined by keyword phrases. You can edit the file or pass your own with `--taxonomy`.
   - **Emerging themes:** 2–3 word phrases that recur across titles, clustered by meaning (`cluster.py`). One idea is often phrased many ways ("habit tracker", "habit tracking", "daily streak"), so similar phrases merge into one theme and their posts are pooled. Each theme is linked to the taxonomy category most of its posts match. A theme with no matching category is marked **new**, which makes it a candidate niche.

3. **Detect explicit demand.** Phrases such as "is there an app", "I'd pay for", "wish someone would build" and "alternative to" mark a signal as an **ask**. An ask shows an unmet need, which is a stronger signal than general popularity.

4. **Score** (`scoring.py`). Each concept gets up to six components. Each component is converted to a percentile across all concepts, so HN points, GitHub stars and chart ranks can be compared. The weighted blend becomes a 0–100 score.

   | Component | Weight | Meaning |
   |---|---:|---|
   | engagement | 0.30 | log-damped attention on matching signals |
   | intent | 0.25 | number of explicit asks |
   | momentum | 0.20 | activity in the recent half of the window vs the older half |
   | volume | 0.15 | number of distinct signals |
   | diversity | 0.10 | number of independent sources that agree |
   | search | 0.15 | Google search interest in the recent half vs the older half (only when Trends data was collected) |

   The weights are normalized, so when no Trends data is present, scoring is exactly what it would be without the search component.

5. **Report** (`report.py`). The Markdown report has a ranked concept table, evidence links for each concept, emerging themes and the top unmet asks. With `--json` it also writes the same data as JSON.

## Tips

- Run it on a schedule with `--save-signals` so you build up a history.
- To go deeper on one domain, point `--taxonomy` at a file of narrow sub-concepts (for example, only fitness app types).
- Set `GITHUB_TOKEN` to raise GitHub's rate limit.
- Google Trends checks one search term per concept, listed in `demand_radar/search_terms.json`. Trends values are relative to each term's own peak, so only a term's growth is scored, not its size. Choose terms that match how people actually search. Google rate-limits these requests heavily: requests are spaced 1.5s apart, and if Google starts refusing, the tool keeps the data it already has.
- Reddit rate-limits anonymous clients. If it fails, run it again later or pass `--sources` without it. A failing source is skipped; it doesn't stop the run.

## Clustering backends

| `--cluster` | Needs | How similarity is measured |
|---|---|---|
| `tfidf` (default) | nothing | 40% shared words (stemmed), 20% similarity of the posts containing each phrase, 40% overlap in taxonomy categories. The category overlap is what joins synonyms like "calorie counter" and "food photo". Without it, this backend is mostly lexical. |
| `sbert` | `pip install sentence-transformers` (downloads `all-MiniLM-L6-v2` on first use) | cosine similarity of sentence embeddings of each phrase plus its top post titles. This catches synonyms the taxonomy doesn't know. |
| `off` | nothing | no clustering: the old flat phrase list |

Phrases are merged with average-linkage clustering until no two groups are more similar than `--cluster-threshold` (defaults: 0.35 for tfidf, 0.55 for sbert). Raise the threshold for tighter themes; lower it for broader ones.

## Troubleshooting

**`CERTIFICATE_VERIFY_FAILED`.** On macOS the tool already trusts every certificate in the Keychain, including company certificates installed by IT. If it still fails:
- **Python from python.org:** run `open "/Applications/Python 3.X/Install Certificates.command"`, using your version number.
- **Work network, VPN or security software that inspects HTTPS:** export your company's root certificate and run `export SSL_CERT_FILE=/path/to/root.pem`.

**`command not found: python`.** Use `python3`.

## Tests

```bash
python -m unittest discover -s tests
```
