import re
import logging
from dataclasses import dataclass, field
from collections import Counter
from collectors.note_collector import NoteArticle
from collectors.hatena_collector import HatenaEntry
import config

logger = logging.getLogger(__name__)


@dataclass
class AnalyzedNote(NoteArticle):
    title_pattern: str = "その他"
    heading_depth: int = 0       # 見出し階層の深さ
    heading_count: int = 0
    structure_summary: str = ""  # 構成の簡易説明


@dataclass
class AnalyzedHatena(HatenaEntry):
    title_pattern: str = "その他"


@dataclass
class PatternStats:
    title_pattern_counts: dict[str, int] = field(default_factory=dict)
    paid_position_counts: dict[str, int] = field(default_factory=dict)
    avg_heading_count: float = 0.0
    top_tags: list[str] = field(default_factory=list)


class ContentAnalyzer:
    def analyze_note_articles(self, articles: list[NoteArticle]) -> tuple[list[AnalyzedNote], PatternStats]:
        analyzed = []
        for a in articles:
            an = AnalyzedNote(**a.__dict__)
            an.title_pattern = self._classify_title(a.title)
            an.heading_count = len(a.headings)
            an.heading_depth = self._max_heading_depth(a.headings)
            an.structure_summary = self._summarize_structure(an)
            analyzed.append(an)

        stats = self._calc_note_stats(analyzed)
        return analyzed, stats

    def analyze_hatena_entries(self, entries: list[HatenaEntry]) -> tuple[list[AnalyzedHatena], PatternStats]:
        analyzed = []
        for e in entries:
            ae = AnalyzedHatena(**e.__dict__)
            ae.title_pattern = self._classify_title(e.title)
            analyzed.append(ae)

        stats = self._calc_hatena_stats(analyzed)
        return analyzed, stats

    def _classify_title(self, title: str) -> str:
        for pattern_name, regex in config.TITLE_PATTERNS.items():
            if re.search(regex, title):
                return pattern_name
        return "その他"

    def _max_heading_depth(self, headings: list[str]) -> int:
        if not headings:
            return 0
        depths = []
        for h in headings:
            if h.startswith("h1"):
                depths.append(1)
            elif h.startswith("h2"):
                depths.append(2)
            elif h.startswith("h3"):
                depths.append(3)
            elif h.startswith("h4"):
                depths.append(4)
        return max(depths) if depths else 0

    def _summarize_structure(self, a: AnalyzedNote) -> str:
        parts = []
        if a.heading_count > 0:
            parts.append(f"見出し{a.heading_count}個（最大h{a.heading_depth}）")
        if a.is_paid:
            pos_label = {"early": "序盤", "middle": "中盤", "late": "終盤"}.get(
                a.paid_position or "", "不明"
            )
            parts.append(f"有料化位置：{pos_label}")
        if a.headings:
            parts.append(f"主見出し: {a.headings[0].split(': ', 1)[-1][:30]}...")
        return " / ".join(parts) if parts else "構成情報なし"

    def _calc_note_stats(self, analyzed: list[AnalyzedNote]) -> PatternStats:
        title_counts = Counter(a.title_pattern for a in analyzed)
        paid_counts = Counter(
            a.paid_position for a in analyzed if a.is_paid and a.paid_position
        )
        avg_h = (
            sum(a.heading_count for a in analyzed) / len(analyzed) if analyzed else 0
        )
        tags = Counter(a.tag for a in analyzed)
        return PatternStats(
            title_pattern_counts=dict(title_counts),
            paid_position_counts=dict(paid_counts),
            avg_heading_count=round(avg_h, 1),
            top_tags=[t for t, _ in tags.most_common(5)],
        )

    def _calc_hatena_stats(self, analyzed: list[AnalyzedHatena]) -> PatternStats:
        title_counts = Counter(a.title_pattern for a in analyzed)
        all_tags: list[str] = []
        for a in analyzed:
            all_tags.extend(a.tags)
        top_tags = [t for t, _ in Counter(all_tags).most_common(5)]
        return PatternStats(
            title_pattern_counts=dict(title_counts),
            top_tags=top_tags,
        )
