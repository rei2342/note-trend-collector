#!/usr/bin/env python3
"""Standard-library-only synthetic preview; never imports the live pipeline."""
import argparse
from html import escape
from pathlib import Path

NOTICE = "架空データの見本です。実際の記事・反応数・調査結果ではありません。"
SCOPE = "外部通信・AI API・メール送信は行いません。本番メールの表示や動作を確認したものではありません。"
FIXTURES = (
    {"id": "N1", "medium": "noteの形式", "title": "会議を開く前に、招待文へ書きたい3行", "tag": "仕事の進め方", "count": 12, "metric": "スキ", "headings": ("会議で決めたいこと", "選択肢を先に置く", "誰が決めるか"), "description": "目的・選択肢・判断する人を揃える、という架空の記事例です。"},
    {"id": "N2", "medium": "noteの形式", "title": "部下の返事を待つ前に、自分の未返信を見直す", "tag": "マネジメント", "count": 7, "metric": "スキ", "headings": None, "description": "本文を取得できなかった場合の表示例です。見出し数をゼロと決めつけません。"},
    {"id": "N3", "medium": "noteの形式", "title": "月末のCSV集計を、どこから減らす？", "tag": "業務改善", "count": 0, "metric": "スキ", "headings": (), "description": "本文は取得できたが見出しがない、という状態の例です。"},
    {"id": "H1", "medium": "はてブの形式", "title": "会議の報告を事前入力に移すときに確かめること", "tag": "ビジネス", "count": 8, "metric": "ブックマーク", "headings": None, "description": "入力と会議を合わせた負担を見る、という架空の話題です。"},
    {"id": "H2", "medium": "はてブの形式", "title": "副業の受注前に、修正回数を決めておく", "tag": "キャリア", "count": None, "metric": "ブックマーク", "headings": None, "description": "反応数を取得できなかった場合の例です。0件とは分けて表示します。"},
)
EDITORIAL = (
    ("見本のデータに書かれていること", "fixture:N1 と fixture:H1 は、会議を開く前の準備を扱う架空の記事です。N2は本文、H2は反応数を取得できなかった状態を再現しています。"),
    ("ここから考える企画の仮説", "会議を減らす一般論より、次の会議招待に使える3行の記入例を渡せないか。対象は、会議を招集する会社員です。"),
    ("まだ分からないこと", "実際の需要、売上、保存数、何が反応の理由だったか。架空の反応数から優劣や成果は判断できません。"),
)
STEPS = ("実際のレポートでは、出典の記事に戻って内容と前提を読む。", "自分の読者のどんな場面に役立つかを一つ決める。", "自分の経験や確認できる資料で、説明と記入例を作る。", "公開前に何を直し、公開後に何を見るかを決める。少数の反応から効果を断定しない。")
CSS = """
*{box-sizing:border-box}body{margin:0;background:#f5f4ef;color:#233537;font:16px/1.8 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;overflow-wrap:anywhere}
main{max-width:960px;margin:auto;padding:28px 22px 60px}header{background:#153d42;color:#fff;padding:30px;border-radius:16px;margin-bottom:22px}
.eyebrow{font-size:12px;letter-spacing:.08em;color:#477b78;font-weight:700}header .eyebrow{color:#b4dbcd}
h1{font-size:clamp(26px,5vw,38px);line-height:1.4;margin:9px 0 14px}h2{font-size:23px;margin:32px 0 12px;line-height:1.5}h3{font-size:20px;line-height:1.6;margin:8px 0 14px}
p{margin:10px 0}.notice{padding:18px 20px;border:1px solid #d3bd70;border-left:5px solid #a18336;background:#fff8df;border-radius:8px}.notice p{margin:3px 0}
.small,.source{font-size:13px;color:#5c6e6d}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.card{padding:22px;background:#fff;border:1px solid #dce4dd;border-radius:12px;min-width:0}
.steps{background:#e5eee8;border-radius:12px;padding:22px}ol,ul{padding-left:24px}li{margin:6px 0}dl{font-size:14px;margin:16px 0}dl>div{display:flex;gap:10px;justify-content:space-between;border-top:1px solid #e4e9e5;padding:7px 0}dt{color:#5c6e6d;flex-shrink:0}dd{margin:0;text-align:right}footer{margin-top:28px;border-top:1px solid #cedbd2;padding-top:16px;font-size:13px;color:#5c6e6d}
@media(max-width:620px){main{padding:16px 14px 36px}header{padding:24px 20px}.grid{grid-template-columns:1fr}.card{padding:20px}h2{font-size:21px}dl>div{flex-wrap:wrap}dd{text-align:left}}
@media print{body{background:#fff}header{color:#233537;background:#fff;border:1px solid #ccc}.grid{display:block}.card{break-inside:avoid;margin-bottom:12px}}
"""


def count_label(item):
    return "未取得（架空の欠損例）" if item["count"] is None else f"{item['count']}件（架空値）"


def heading_label(item):
    if item["medium"] != "noteの形式":
        return "対象外"
    return "未取得" if item["headings"] is None else f"{len(item['headings'])}個（架空値）"


def render_html(fixtures=FIXTURES):
    e = lambda value: escape(str(value), quote=True)
    cards = []
    for item in fixtures:
        headings = item["headings"]
        heading_list = "<ul>" + "".join(f"<li>{e(h)}</li>" for h in headings) + "</ul>" if headings else ""
        cards.append(f"""<article class="card"><div class="eyebrow">{e(item['medium'])} · fixture:{e(item['id'])}</div>
<h3>{e(item['title'])}</h3><p>{e(item['description'])}</p><dl><div><dt>分類</dt><dd>{e(item['tag'])}</dd></div>
<div><dt>{e(item['metric'])}</dt><dd>{e(count_label(item))}</dd></div><div><dt>公開部分の見出し</dt><dd>{e(heading_label(item))}</dd></div></dl>
{heading_list}<p class="source">出典：同梱の合成フィクスチャ fixture:{e(item['id'])}。実在記事へのリンクはありません。</p></article>""")
    editorial = "".join(f"<p><strong>{e(title)}</strong><br>{e(body)}</p>" for title, body in EDITORIAL)
    steps = "".join(f"<li>{e(step)}</li>" for step in STEPS)
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>週次レポートの内容見本｜架空データ・オフライン</title><style>{CSS}</style></head><body><main>
<header><div class="eyebrow">AKIRA · OFFLINE SAMPLE</div><h1>集めた記事を<br>次の企画に変える</h1><p>週次レポートの内容見本。原文で確かめることと、次に試すことを分けます。</p></header>
<aside class="notice"><p><strong>{e(NOTICE)}</strong></p><p class="small">{e(SCOPE)}</p><p class="small">この見本はあらかじめ用意した固定文です。AI APIによる自動分析は行っていません。実データの最新トレンドではありません。</p></aside>
<h2>1. 観測と仮説を分ける</h2><section class="steps">{editorial}</section>
<h2>2. 収集記事の表示例</h2><p class="small">{len(fixtures)}件すべて同梱の架空データです。未取得と0件の表示の違いも確認できます。</p><div class="grid">{''.join(cards)}</div>
<h2>3. 今週の企画を1本に絞るために</h2><section class="steps"><ol>{steps}</ol><p>例：会議招待の見本を用意し、実際に招集する人へ、判断に足りない情報がないか確認する。</p></section>
<footer>このファイルはローカルで開く閲覧用サンプルです。通信先、外部画像、スクリプトは含みません。GmailやAIの設定、課金、メール送信は行われていません。本番メールは別の表示形式です。</footer></main></body></html>"""


def render_text(fixtures=FIXTURES):
    lines = ["週次レポートの内容見本｜架空データ・オフライン", NOTICE, SCOPE, "あらかじめ用意した固定文です。AI APIによる自動分析や実データの最新トレンドではありません。", ""]
    for title, body in EDITORIAL:
        lines.extend([title, body, ""])
    for item in fixtures:
        lines.extend([f"[{item['id']}] {item['title']}", item["description"], f"分類：{item['tag']} ／ {item['metric']}：{count_label(item)}", f"公開部分の見出し：{heading_label(item)}"])
        lines.extend(f"・{heading}" for heading in (item["headings"] or ()))
        lines.extend([f"出典：同梱の合成フィクスチャ fixture:{item['id']}。実在記事へのリンクはありません。", ""])
    lines.append("企画を1本に絞るために")
    lines.extend(f"{i}. {step}" for i, step in enumerate(STEPS, 1))
    lines.append("本番メールは別の表示形式です。この見本は送信確認ではありません。")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="架空データの内容見本を保存。通信・API・送信・環境設定の読込は行いません。")
    parser.add_argument("--output-dir", type=Path, default=Path("preview_output"), help="保存先。既存の見本ファイルは上書きしません。")
    args = parser.parse_args(argv)
    paths = (args.output_dir / "sample_report.html", args.output_dir / "sample_report.txt")
    if any(path.exists() or path.is_symlink() for path in paths):
        parser.error("見本ファイルが既にあります。別の --output-dir を指定してください。")
    created = []
    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for path, text in zip(paths, (render_html(), render_text())):
            with path.open("x", encoding="utf-8") as handle:
                created.append(path)
                handle.write(text)
    except OSError:
        for path in created:
            path.unlink(missing_ok=True)
        parser.exit(1, "見本を保存できませんでした。保存先の権限を確認してください。\n")
    print("架空データの見本を保存しました。通信・API利用・メール送信は0回です。")
    print("保存先の sample_report.html をブラウザで開いてください。sample_report.txt も保存済みです。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
