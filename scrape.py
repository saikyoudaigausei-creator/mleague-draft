"""M.LEAGUE 公式サイトから試合結果を取得し、ファンタジー用の data.json と index.html を生成する。

使い方:
    python scrape.py                 # 今シーズン
    python scrape.py 2025-season     # 過去シーズン(動作確認用)

データ源:
    /games/            … 日付・回戦ごとの各選手の得点pt (これを積み上げて日別推移を作る)
    /stats/            … 選手→チームの対応と、累計ポイント(検算用)
"""
import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
JST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"

# チームカラー(グラフ用)。名前は stats ページの表記を空白除去したもの。
TEAM_COLORS = {
    "赤坂ドリブンズ": "#2e7d32",
    "EX風林火山": "#c62828",
    "KONAMI麻雀格闘倶楽部": "#6a1b9a",
    "渋谷ABEMAS": "#f9a825",
    "セガサミーフェニックス": "#ef6c00",
    "TEAMRAIDEN/雷電": "#f06292",
    "U-NEXTPirates": "#1565c0",
    "KADOKAWAサクラナイツ": "#ad1457",
    "BEASTX": "#37474f",
    "EARTHJETS": "#00897b",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def norm(s):
    return re.sub(r"\s+", "", html.unescape(s))


def parse_stats(h):
    """stats ページ → {選手名: {"team":…, "pt":…}}, [チーム名(表示用)]"""
    players, teams = {}, []
    for sec in re.findall(r'<section class="p-stats__team".*?</section>', h, re.S):
        m = re.search(r'<h2 class="p-stats__teamName">(.*?)</h2>', sec, re.S)
        team_disp = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        team = norm(team_disp)
        teams.append({"key": team, "name": team_disp})
        names = [norm(x) for x in re.findall(r'<th scope="col">(.*?)</th>', sec)]
        pm = re.search(r'<th scope="row">ポイント</th>(.*?)</tr>', sec, re.S)
        pts = [float(x) for x in re.findall(r"<td>(.*?)</td>", pm.group(1))] if pm else []
        for i, n in enumerate(names):
            players[n] = {"team": team, "pt": pts[i] if i < len(pts) else 0.0}
    return players, teams


def parse_games(h):
    """games ページ → [{date, no, results:[{player, rank, pt, img, badge}]}]"""
    games = []
    blocks = re.split(r'<div class="c-modal2" id="js-modal-key', h)[1:]
    for b in blocks:
        key = re.match(r"(\d{8})-(\d+)", b)
        if not key:
            continue  # テンプレート用のダミーブロック
        d = key.group(1)
        date = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        cols = re.split(r'<div class="p-gamesResult__column">', b)[1:]
        for ci, col in enumerate(cols, 1):
            numm = re.search(r'p-gamesResult__number">(.*?)<', col)
            results = []
            for li in re.findall(r"<li>.*?</li>", col, re.S):
                name = re.search(r'p-gamesResult__name">(.*?)</div>', li, re.S)
                pt = re.search(r'p-gamesResult__point">\s*(.*?)\s*</div>', li, re.S)
                rank = re.search(r"rank-badge is-(\d)", li)
                if not name or not name.group(1).strip():
                    continue  # 未消化の試合(プレースホルダ)
                ptxt = norm(pt.group(1)).replace("pt", "").replace("▲", "-").replace("−", "-")
                try:
                    p = float(ptxt)
                except ValueError:
                    continue
                imgs = re.findall(r'<img src="([^"]*)"', li)
                results.append({
                    "player": norm(name.group(1)),
                    "rank": int(rank.group(1)) if rank else None,
                    "pt": p,
                    "img": imgs[0] if imgs else "",
                    "badge": imgs[1] if len(imgs) > 1 else "",
                })
            if len(results) == 4:
                games.append({
                    "date": date,
                    "match": int(key.group(2)),
                    "no": numm.group(1).strip() if numm else f"第{ci}回戦",
                    "results": results,
                })
    return games


def main():
    season = sys.argv[1] if len(sys.argv) > 1 else ""
    games_url = f"https://m-league.jp/games/{season + '/' if season else ''}"
    print("fetch", games_url)
    games = parse_games(fetch(games_url))
    print("fetch https://m-league.jp/stats/")
    stats, teams = parse_stats(fetch("https://m-league.jp/stats/"))

    # 選手→チーム: stats ページ優先。載っていない選手(過去シーズン等)はチームバッジ画像から推定
    badge_team = {}
    for g in games:
        for r in g["results"]:
            if r["player"] in stats and r["badge"]:
                badge_team[r["badge"]] = stats[r["player"]]["team"]
    players = {}
    for g in games:
        for r in g["results"]:
            team = stats.get(r["player"], {}).get("team") or badge_team.get(r["badge"], "不明")
            players.setdefault(r["player"], {"team": team, "img": r["img"]})
            del r["img"], r["badge"]

    # 検算: 試合結果の積み上げ と stats ページの累計 が一致するか(今シーズンのみ)
    if not season:
        total = {}
        for g in games:
            for r in g["results"]:
                total[r["player"]] = round(total.get(r["player"], 0) + r["pt"], 1)
        bad = [(n, total.get(n, 0), s["pt"]) for n, s in stats.items()
               if abs(total.get(n, 0) - s["pt"]) > 0.05]
        print("検算:", "OK 全選手一致" if not bad else f"不一致 {bad}")

    team_list = [dict(t, color=TEAM_COLORS.get(t["key"], "#888")) for t in teams]
    data = {
        "season": season or "current",
        "updated": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        "teams": team_list,
        "players": players,
        "games": games,
    }
    # 試合結果が前回と同じなら data.json を書き換えない(GitHub Actions で無駄なコミットを出さないため)
    data_path = ROOT / "data" / "data.json"
    old = json.loads(data_path.read_text(encoding="utf-8")) if data_path.exists() else None
    if old and old.get("games") == games and old.get("players") == players:
        data = old
        print("新しい試合結果なし")
    else:
        data_path.parent.mkdir(exist_ok=True)
        data_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print("data/data.json を更新")

    days = sorted({g["date"] for g in games})
    print(f"{len(games)}試合 / {len(days)}日 / 最終 {days[-1] if days else '-'}")

    # league.json は手元だけに置く(リポジトリには入れない)。無ければページは作らない
    if not (ROOT / "league.json").exists():
        return
    league = json.loads((ROOT / "league.json").read_text(encoding="utf-8"))
    unknown = [p for m in league["members"] for p in m.get("players", []) if norm(p) not in players and norm(p) not in stats]
    if unknown:
        print("⚠ league.json に結果の無い選手名:", unknown)

    tpl = (ROOT / "template.html").read_text(encoding="utf-8")
    out = tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False)) \
             .replace("/*__LEAGUE__*/null", json.dumps(league, ensure_ascii=False))
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "index.html").write_text(out, encoding="utf-8")
    print("→ docs/index.html")


if __name__ == "__main__":
    main()
