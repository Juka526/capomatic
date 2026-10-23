"""Local evaluation server that retains the exact immutable capture evidence.

Use only with the isolated development inputs. This adds no HTTP endpoint and
changes no recognition decision; it copies SourcePage bytes before returning.
"""
import argparse
import hashlib
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    from backend.omr_v3.source_layout import SourcePage
    original = SourcePage.capture

    def capture(cls, png, omr, metadata):
        page = original(png, omr, metadata)
        folder = args.out / hashlib.sha256(page.png + page.metadata_json).hexdigest()
        folder.mkdir(exist_ok=True)
        for name, data in [('source.png', page.png), ('recognition.omr', page.omr),
                           ('coordinates.json', page.metadata_json),
                           ('ownership.json', page.evidence_json),
                           ('ink-masks.zip', page.ink_masks)]:
            (folder / name).write_bytes(data)
        return page

    SourcePage.capture = classmethod(capture)
    import uvicorn
    uvicorn.run('backend.api.main:app', host='0.0.0.0', port=args.port)


if __name__ == '__main__':
    main()
