"""
ルールベースのトレンドサマリー生成（Claude API不使用）
収集・分析データから定型ロジックでレポートを組み立てる。
"""

from collections import Counter
from collectors.x_collector import XPost
from analyzer import AnalyzedNote, AnalyzedHatena, PatternStats


class TrendSummarizer:
    def generate_summary(
        self,
        note_data: tuple[list[AnalyzedNote], PatternStats],
        hatena_data: tuple[list[AnalyzedHatena], PatternStats],
        x_posts: list[XPost],
    ) -> str:
        note_articles, note_stats = note_data
        hatena_entries, hatena_stats = hatena_data

        sections = [
            self._section_key_themes(note_articles, hatena_entries, x_posts),
            self._section_winning_patterns(note_stats),
            self._section_pickup(note_articles, hatena_entries),
            self._section_content_ideas(note_articles, hatena_entries, note_stats),
            self._section_one_liner(note_stats, hatena_stats),
        ]
        return "\n\n".join(sections)

    # ------------------------------------------------------------------ #
    # セクション生成
    # ------------------------------------------------------------------ #

    def _section_key_themes(
        self,
        note_articles: list[AnalyzedNote],
        hatena_entries: list[AnalyzedHatena],
        x_posts: list[XPost],
    ) -> str:
        themes = self._extract_themes(note_articles, hatena_entries)
        lines = ["## 今週のトレンドサマリー", "", "### 1. 今週のキーテーマ"]
        for theme, reason in themes[:5]:
            lines.append(f"- **{theme}** — {reason}")
        return "\n".join(lines)

    def _section_winning_patterns(self, note_stats: PatternStats) -> str:
        lines = ["### 2. 勝ちパターン分析"]

        # タイトルパターン
        top_patterns = sorted(note_stats.title_pattern_counts.items(), key=lambda x: -x[1])
        if top_patterns:
            top_name, top_cnt = top_patterns[0]
            lines.append(f"- **タイトルの型**: 「{top_name}」が最多（{top_cnt}件）。" + self._pattern_tip(top_name))

        # 有料化位置
        if note_stats.paid_position_counts:
            pos_top = max(note_stats.paid_position_counts, key=note_stats.paid_position_counts.get)
            pos_label = {"early": "序盤（〜35%）", "middle": "中盤（35〜65%）", "late": "終盤（65%〜）"}.get(pos_top, pos_top)
            lines.append(f"- **有料化の位置**: {pos_label}が最多。" + self._paid_pos_tip(pos_top))
        else:
            lines.append("- **有料化の位置**: 今週は無料記事が中心でした。")

        # 見出し構成
        avg = note_stats.avg_heading_count
        if avg >= 6:
            h_comment = "見出しが多く、読み飛ばしやすい構成が好まれています。"
        elif avg >= 3:
            h_comment = "程よい見出し数で、テンポよく読める構成が主流です。"
        else:
            h_comment = "見出しが少なめ。体験談・エッセイ系が多い週でした。"
        lines.append(f"- **見出し構成**: 平均{avg}個 — {h_comment}")

        return "\n".join(lines)

    def _section_pickup(
        self,
        note_articles: list[AnalyzedNote],
        hatena_entries: list[AnalyzedHatena],
    ) -> str:
        lines = ["### 3. 今週注目の記事ピックアップ"]

        # noteトップ2
        top_notes = sorted(note_articles, key=lambda a: a.like_count, reverse=True)[:2]
        for a in top_notes:
            reason = self._pickup_reason_note(a)
            lines.append(f"- **[note]** [{a.title}]({a.url})（いいね {a.like_count}）")
            lines.append(f"  - {reason}")

        # はてブトップ1
        if hatena_entries:
            top_h = max(hatena_entries, key=lambda e: e.bookmark_count)
            lines.append(f"- **[はてブ]** [{top_h.title}]({top_h.url})（ブクマ {top_h.bookmark_count}）")
            lines.append(f"  - タイトル型「{top_h.title_pattern}」で高いブックマークを獲得。")

        return "\n".join(lines)

    def _section_content_ideas(
        self,
        note_articles: list[AnalyzedNote],
        hatena_entries: list[AnalyzedHatena],
        note_stats: PatternStats,
    ) -> str:
        lines = ["### 4. 来週のコンテンツアイデア"]
        ideas = self._generate_ideas(note_articles, hatena_entries, note_stats)
        for idea in ideas[:5]:
            lines.append(f"- {idea}")
        return "\n".join(lines)

    def _section_one_liner(
        self, note_stats: PatternStats, hatena_stats: PatternStats
    ) -> str:
        top_note_tag = note_stats.top_tags[0] if note_stats.top_tags else "キャリア"
        top_pattern = ""
        if note_stats.title_pattern_counts:
            top_pattern = max(note_stats.title_pattern_counts, key=note_stats.title_pattern_counts.get)

        line = f"### 5. 一言まとめ\n「**{top_note_tag}**」テーマ × 「**{top_pattern}**」型タイトルの組み合わせが今週の主役。"
        return line

    # ------------------------------------------------------------------ #
    # ヘルパー
    # ------------------------------------------------------------------ #

    def _extract_themes(
        self,
        note_articles: list[AnalyzedNote],
        hatena_entries: list[AnalyzedHatena],
    ) -> list[tuple[str, str]]:
        """全記事タイトル・概要からキーワード頻度でテーマを抽出"""
        THEME_KEYWORDS = {
            "AI活用": ["AI", "ChatGPT", "Claude", "生成AI", "自動化", "プロンプト"],
            "キャリア転換": ["転職", "独立", "フリーランス", "起業", "副業", "退職"],
            "収益化": ["収益", "マネタイズ", "有料", "稼ぐ", "収入", "報酬"],
            "スキルアップ": ["スキル", "勉強", "学習", "資格", "習得"],
            "マーケティング": ["マーケティング", "集客", "SNS", "フォロワー", "バズ"],
            "生産性": ["生産性", "効率", "時短", "タスク", "習慣"],
            "プロデューサー": ["プロデューサー", "プロデュース", "企画", "ディレクション"],
        }

        all_text = " ".join(
            [a.title + " " + a.description for a in note_articles]
            + [e.title + " " + e.description for e in hatena_entries]
        )

        results = []
        for theme, keywords in THEME_KEYWORDS.items():
            count = sum(all_text.count(kw) for kw in keywords)
            if count > 0:
                hit_kw = [kw for kw in keywords if kw in all_text]
                results.append((theme, count, hit_kw))

        results.sort(key=lambda x: -x[1])
        return [
            (theme, f"「{'・'.join(kws[:3])}」関連の記事が複数登場")
            for theme, _, kws in results
            if kws
        ]

    def _pattern_tip(self, pattern: str) -> str:
        tips = {
            "数字リスト": "具体性と読みやすさで高エンゲージメントを獲得しやすい型。",
            "疑問形": "読者の悩みに直接刺さるタイトルで検索流入にも強い。",
            "ハウツー": "実用性訴求で保存率が高く、拡散されやすい。",
            "体験談": "一人称の生々しさが共感を生みやすい型。",
            "まとめ": "情報収集ニーズに応える型。SNS拡散と相性が良い。",
            "比較": "意思決定を助ける型。検索意図と合致しやすい。",
            "警告・逆説": "損失回避心理に訴求する型。クリック率が高い傾向。",
            "完全ガイド": "保存版コンテンツとして長期的な流入が期待できる型。",
        }
        return tips.get(pattern, "安定したパフォーマンスが期待できる型。")

    def _paid_pos_tip(self, pos: str) -> str:
        tips = {
            "early": "序盤で有料化 → 冒頭で強いフックが必要。ファン向け戦略。",
            "middle": "中盤で有料化 → 無料部分で十分な価値提示が鍵。",
            "late": "終盤で有料化 → 無料でほぼ読める設計。信頼獲得型。",
        }
        return tips.get(pos, "")

    def _pickup_reason_note(self, a: AnalyzedNote) -> str:
        reasons = []
        if a.title_pattern != "その他":
            reasons.append(f"タイトル型「{a.title_pattern}」")
        if a.is_paid and a.paid_position:
            label = {"early": "序盤", "middle": "中盤", "late": "終盤"}.get(a.paid_position, "")
            reasons.append(f"有料化{label}配置")
        if a.heading_count >= 5:
            reasons.append(f"見出し{a.heading_count}個の構成")
        if not reasons:
            reasons.append("シンプルな構成でいいね多数獲得")
        return "、".join(reasons) + "が奏功した可能性。"

    def _generate_ideas(
        self,
        note_articles: list[AnalyzedNote],
        hatena_entries: list[AnalyzedHatena],
        note_stats: PatternStats,
    ) -> list[str]:
        ideas = []
        top_tag = note_stats.top_tags[0] if note_stats.top_tags else "キャリア"
        top_pattern = ""
        if note_stats.title_pattern_counts:
            top_pattern = max(note_stats.title_pattern_counts, key=note_stats.title_pattern_counts.get)

        # パターン×タグの組み合わせアイデア
        pattern_templates = {
            "数字リスト": f"「{top_tag}で成果を出す人がやっている5つの習慣」",
            "疑問形": f"「なぜ{top_tag}で失敗する人が多いのか？本質的な原因を解説」",
            "ハウツー": f"「{top_tag}で月収を上げるための具体的なステップ」",
            "体験談": f"「{top_tag}に挑戦して3ヶ月で変わったこと【リアルな話】」",
            "警告・逆説": f"「{top_tag}でやってはいけない3つのミス」",
            "完全ガイド": f"「{top_tag}完全ガイド【2026年版・保存版】」",
        }
        if top_pattern in pattern_templates:
            ideas.append(pattern_templates[top_pattern])

        # 汎用アイデア
        ideas += [
            f"「{top_tag}×AI活用」の掛け合わせテーマ（両トレンドを捉えたコンテンツ）",
            "今週のはてブ人気記事を切り口に、note視点の考察記事",
            "有料設計を中盤に置いた体験談記事（今週の主流パターンを踏襲）",
            f"「{top_tag}を始めて気づいた、誰も教えてくれない現実」（体験談×警告型）",
        ]
        return ideas
