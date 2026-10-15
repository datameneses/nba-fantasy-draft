"""Pull season totals, game logs and current teams from Sleeper and score them with the league's rules -> data.json.
Run: python3 build_data.py && python3 build.py   (about 80 requests, a few minutes)"""
import json, pathlib, time, urllib.request
from collections import Counter, defaultdict

SEASONS = (2023, 2024, 2025)           # 2023 = the 2023-24 season
PROJ = '2026-27'                       # last season's production under each player's current team
POSITIONS = ('PG', 'SG', 'SF', 'PF', 'C')
# Universo BSB Fantasy scoring: stat -> points per occurrence
SCORING = dict(pts=0.5, reb=0.75, ast=1, stl=2, blk=2, to=-1, dd=1, td=2, tf=-2, ff=-2, tpm=0.5, b40=2, b50=2, ba15=1, br20=1)

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'nba-fantasy-draft'})
    return json.load(urllib.request.urlopen(req, timeout=120))

def bonus_counts(y):
    """Count bonus games from game logs (Sleeper's season-level bonus fields are 0/1 flags, not counts).
    Base stats come from the official season totals instead, so they match games played."""
    agg = defaultdict(Counter)
    for week in range(1, 60):
        rows = get(f'https://api.sleeper.com/stats/nba/{y}/{week}?season_type=regular')
        if not rows:
            break
        for r in rows:
            s, a = r['stats'], agg[r['player_id']]
            a['b40'] += s.get('pts', 0) >= 40
            a['b50'] += s.get('pts', 0) >= 50
            a['ba15'] += s.get('ast', 0) >= 15
            a['br20'] += s.get('reb', 0) >= 20
        time.sleep(0.25)
    return agg

out = []
for y in SEASONS:
    bonus = bonus_counts(y)
    for r in get(f'https://api.sleeper.com/stats/nba/{y}?season_type=regular&order_by=pts_ppr'):
        p = r['player']
        gp = r['stats'].get('gp')
        if r['player_id'][:4] == 'TEAM' or not gp or p['position'] not in POSITIONS:
            continue
        st, b = r['stats'], bonus[r['player_id']]
        t = Counter({k: st.get(k, 0) for k in SCORING if k not in ('b40', 'b50', 'ba15', 'br20')})
        t.update({k: b[k] for k in ('b40', 'b50', 'ba15', 'br20')})
        fp = sum(w * t[k] for k, w in SCORING.items())
        g = lambda k: round(t[k] / gp, 1)
        out.append(dict(id=r['player_id'], season=f"{y}-{str(y + 1)[2:]}", name=f"{p['first_name']} {p['last_name']}",
            team=r['team'] or 'FA', pos=p['position'], gp=int(gp), fp=round(fp, 2), fppg=round(fp / gp, 1),
            pts=g('pts'), reb=g('reb'), ast=g('ast'), stl=g('stl'), blk=g('blk'), to=g('to'), tpm=g('tpm'),
            td=int(t['td']), dd=int(t['dd']), b40=int(t['b40']), b50=int(t['b50']), ba15=int(t['ba15']),
            br20=int(t['br20']), tf=int(t['tf']), ff=int(t['ff'])))
    print(y, 'done', flush=True)

now = get('https://api.sleeper.app/v1/players/nba')
last = f"{SEASONS[-1]}-{str(SEASONS[-1] + 1)[2:]}"
for r in [r for r in out if r['season'] == last]:
    out.append(dict(r, season=PROJ, team=(now.get(r['id']) or {}).get('team') or 'FA', src=last))
out.sort(key=lambda r: (r['season'], -r['fp']))
(pathlib.Path(__file__).parent / 'data.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
print(len(out), 'rows')
