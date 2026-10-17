"""Developer-only annotations. Never erase or draw replacement score symbols."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from .plan import LayoutEditPlan
from .visual_graph import VisualScoreGraph

COLORS = {
    'source': '#008744',
    'target': '#0066ff',
    'ambiguous': '#e68a00',
    'unmatched': '#e00030',
    'protected': '#b000b5',
    'beam': '#00a1a1',
    'slur': '#7b43c5',
    'key': '#996000',
}


def write_diagnostics(
    source: Path,
    graph: VisualScoreGraph,
    plan: LayoutEditPlan,
    out: Path,
    *,
    page_id: str | None = None,
) -> dict:
    """Write plan/summary JSON and a source-preserving annotation composite."""
    if page_id is None:
        if len(graph.pages) != 1:
            raise ValueError('Choose an explicit page for a multi-sheet diagnostic')
        page_id = graph.pages[0].id
    page = next((p for p in graph.pages if p.id == page_id), None)
    if page is None:
        raise ValueError('Unknown page')
    with Image.open(source) as image:
        if image.size != (page.width, page.height):
            raise ValueError('Source raster and Audiveris coordinate dimensions differ')
        base = image.convert('RGBA')
    layer = Image.new('RGBA', base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    def box(region, color, width=2):
        if region:
            draw.rectangle(region, outline=color, width=width)

    def circle(x, y, color, radius=5):
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=color, width=2)

    for region in plan.protected_regions:
        if region.page == page_id:
            box(region.bbox, COLORS['protected'])
    for group in plan.beam_groups:
        if group.page == page_id:
            box(group.source_region, COLORS['beam'])
    for slur in plan.slurs:
        if slur.page != page_id or len(slur.curve) != 4:
            continue
        p0, p1, p2, p3 = slur.curve
        points = []
        for i in range(65):
            t = i / 64
            points.append(
                tuple(
                    (1 - t) ** 3 * p0[d]
                    + 3 * (1 - t) ** 2 * t * p1[d]
                    + 3 * (1 - t) * t * t * p2[d]
                    + t**3 * p3[d]
                    for d in (0, 1)
                )
            )
        draw.line(points, fill=COLORS['slur'], width=2)
    for key in plan.key_signatures:
        if key.page == page_id:
            box(key.region, COLORS['key'], 3)
    ambiguous = {h for m in plan.matches.notes if m.status == 'AMBIGUOUS' for h in m.candidate_ids}
    for ident in plan.matches.unmatched_visual_ids:
        symbol = graph.symbols[ident]
        if symbol.page == page_id:
            box(symbol.geometry.region, COLORS['ambiguous' if ident in ambiguous else 'unmatched'])
    for move in plan.note_moves:
        if move.page != page_id:
            continue
        draw.line(
            (move.source_x, move.source_y, move.target_x, move.target_y),
            fill=COLORS['target'],
            width=2,
        )
        circle(move.source_x, move.source_y, COLORS['source'], 7)
        circle(move.target_x, move.target_y, COLORS['target'], 4)
    # Put the legend outside the page so titles and margins stay readable.
    composite = Image.new('RGB', (base.width + 430, max(base.height, 560)), 'white')
    composite.paste(Image.alpha_composite(base, layer).convert('RGB'), (0, 0))
    legend = ImageDraw.Draw(composite)
    x, y = base.width + 12, 12
    legend.text((x, y), 'V4 PHASE 1 - DIAGNOSTIC ONLY', fill='black')
    y += 24
    for label, color in COLORS.items():
        legend.text((x, y), label, fill=color)
        y += 20
    for name, value in plan.metrics:
        legend.text((x, y), f'{name}: {value}', fill='black')
        y += 16
    unresolved = [m for m in plan.matches.notes if m.status != 'MATCHED']
    if unresolved:
        y += 16
        legend.text((x, y), 'Unlocated semantic events (full list in plan.json):', fill='black')
        y += 20
        for match in unresolved[: max(0, (composite.height - y - 20) // 16)]:
            legend.text(
                (x, y),
                f'{match.status}: {match.note.id} {match.note.pitch}',
                fill=COLORS['ambiguous' if match.status == 'AMBIGUOUS' else 'unmatched'],
            )
            y += 16
    out.mkdir(parents=True, exist_ok=True)
    summary = graph.summary() | dict(plan.metrics)
    summary.update(
        diagnostic_only=True,
        raster_page=page_id,
        blockers=plan.blockers,
        confidence_interpretation='Audiveris grades, not calibrated match probabilities',
    )
    (out / 'plan.json').write_text(plan.to_json(), encoding='utf-8')
    (out / 'graph-summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n',
        encoding='utf-8',
    )
    layer.save(out / 'diagnostic-annotations.png')
    composite.save(out / 'diagnostic-overlay.png')
    return summary
