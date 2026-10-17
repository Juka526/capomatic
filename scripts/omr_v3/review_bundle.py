"""Copy a bounded review bundle; full evidence stays in the Actions artifact."""
import argparse
import json
import shutil
from pathlib import Path


def build(source: Path, destination: Path) -> None:
    """Publish summary/text and at most four representative images, at most 12 MiB."""
    destination.mkdir(parents=True, exist_ok=True)
    budget = 12 * 1024 * 1024
    names = ['REPORT.generated.md', 'summary.json', 'api-benchmark.txt',
             'multipage-smoke.txt', 'api-fallback.txt', 'api-zip-listing.txt', 'api-container-stats.txt']
    for name in names:
        path = source / name
        if path.is_file() and path.stat().st_size <= min(budget, 2 * 1024 * 1024):
            shutil.copy2(path, destination / name)
            budget -= path.stat().st_size
    images = sorted(source.glob('*/side_by_side*.png'))
    # Spread the small visual sample across the alphabetically ordered corpus.
    selected = []
    summary = source / 'summary.json'
    if summary.exists():
        runs = json.loads(summary.read_text()).get('runs', [])
        for mode in ('full_score', 'chord_only', 'error'):
            for run in runs:
                candidates = sorted((source / run['id']).glob('side_by_side*.png'))
                if run.get('mode') == mode and candidates:
                    selected.append(candidates[0])
                    break
    for path in images:
        if len(selected) >= 4:
            break
        if path not in selected:
            selected.append(path)
    for path in selected:
        if path.stat().st_size <= min(budget, 2 * 1024 * 1024):
            shutil.copy2(path, destination / (path.parent.name + '-' + path.name))
            budget -= path.stat().st_size
    (destination / 'README.md').write_text(
        '# V3 review evidence\n\nFull PDFs, MusicXML, JSON, images and logs are in the '
        '`omr-v3-evidence` Actions artifact for this commit. This branch is a bounded '
        'review sample, not the full dataset.\n\nReproduce with the pinned Dockerfile and '
        'the evaluation command in `.github/workflows/omr-v3-eval.yml`. Fresh synthetic '
        'seeds are recorded in summary.json; do not call them blind after tuning.\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    build(args.source, args.destination)
