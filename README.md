# FreeTier Radar

A hand-verified directory of developer free tiers — real limits, hidden traps, verification dates, and a Graveyard of free tiers that died. Single self-contained static site, zero dependencies, $0 to run.

## Project layout

```
freetier-radar/
├── index.html            # the whole site (data embedded, works offline)
├── data/tools.json       # source of truth: 21 tools + graveyard
├── scripts/build.py      # re-embeds tools.json into index.html
├── scripts/check_changes.py  # watches pricing pages for changes
└── snapshots/            # pricing-page snapshots (created on first check)
```

## Editing data

1. Edit `data/tools.json` (add a tool, fix a limit, bump a `verified` date).
2. Run `python3 scripts/build.py` — it re-embeds the data into `index.html`.
3. Commit and push. That's the entire pipeline.

## Deploy for free

### Option A — GitHub Pages (simplest)

1. Create a public repo (e.g. `freetier-radar`) and push these files.
2. Repo → Settings → Pages → Source: `Deploy from a branch`, branch `main`, folder `/ (root)`.
3. Site goes live at `https://<username>.github.io/freetier-radar/` within a minute or two.
4. Custom domain (optional, ~$10/yr for the domain, hosting stays free): add the domain in the same Pages settings and create a CNAME record at your registrar.

### Option B — Cloudflare Pages (faster CDN, better analytics)

1. Push the repo to GitHub.
2. dash.cloudflare.com → Workers & Pages → Create → Pages → connect the repo.
3. Build command: *(leave empty)*, output directory: `/`. Deploy.
4. Free web analytics can be enabled in one click — useful once traffic starts.

Either way the site fits comfortably inside the free tiers it describes — a nice sales point in itself.

## Keeping data fresh (the moat)

Weekly, run:

```bash
python3 scripts/check_changes.py
```

It fetches every `pricing_url`, compares against the last snapshot and prints the tools whose pricing page changed. Re-verify those by hand, update `tools.json`, bump `verified`, run `build.py`, push.

To automate the *detection* with GitHub Actions (free for public repos), add `.github/workflows/watch.yml`:

```yaml
name: watch-pricing
on:
  schedule:
    - cron: "0 6 * * 1"   # Mondays 06:00 UTC
  workflow_dispatch:
jobs:
  check:
    runs-on: ubuntu-latest
    permissions: { contents: write, issues: write }
    steps:
      - uses: actions/checkout@v4
      - run: python3 scripts/check_changes.py > report.txt || true
      - run: cat report.txt
      - name: Open issue if changes found
        run: |
          if grep -q "RE-VERIFY" report.txt; then
            gh issue create --title "Pricing pages changed $(date +%F)" --body "$(cat report.txt)"
          fi
        env: { GH_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
      - name: Commit snapshots
        run: |
          git config user.name "radar-bot"
          git config user.email "bot@users.noreply.github.com"
          git add snapshots && git diff --cached --quiet || git commit -m "chore: update pricing snapshots"
          git push
```

Every Monday you get a GitHub issue listing exactly what to re-check. Manual verification stays human — that's the credibility the whole product rests on.

## Launch checklist (from the plan, section 15)

Week 1 — soft checks:
- Deploy, verify on mobile, submit the URL to Google Search Console (free) and request indexing.
- Make the repo public with a clear "found an error? PR welcome" note in this README — corrections are free content and free trust.

Week 2 — the launch content piece:
- Write "The Free Tier Graveyard: every dev free tier that died, 2022–2026" as a post (the graveyard section is the hook — it's shareable and slightly contrarian).
- Post to r/webdev and r/selfhosted (different days, follow each sub's self-promo rules), dev.to, and Hacker News as Show HN ("Show HN: I verify dev free tiers by hand and track the ones that die"). Tuesday–Thursday, morning US time, and stay in the comments all day — comment quality decides HN outcomes.

Ongoing (fits in 5–15 h/week):
- Weekly: run the checker, update entries, one changelog tweet/post per meaningful change ("Netlify free now pauses sites — verified today").
- Monthly: add 3–5 tools by request (add a "suggest a tool" GitHub issue template).
- The update feed itself is the content: every pricing change you catch first is a Reddit/HN comment opportunity.

Monetization later, in this order (per the plan): GitHub Sponsors link → tasteful "recommended for indie devs" section clearly marked as such → newsletter of pricing changes. Never sell placement in the rankings; the FAQ already promises that publicly.
