"""Prepare a neutral workflow schedule over the unchanged GT-02 packet."""

import argparse
import json
from pathlib import Path

from scripts.research.gt02_reference_packet import require, verify_packet
from scripts.research.paired_ground_truth_01 import dump, sha

# User-requested diagnostic coverage, not a random accuracy sample.
PILOT = {'A': (5, 25, 26, 35, 36), 'G': (26, 27), 'Bb': (1, 3, 8, 9, 15, 16, 17)}


def prepare(packet, private_index, out):
    packet, private_index, out = map(Path, (packet, private_index, out))
    require(not out.exists(), 'New output directory required')
    for protected in (packet.parent.resolve(), private_index.parent.resolve()):
        require(
            out.resolve() != protected and protected not in out.resolve().parents,
            'Do not write inside GT-02 evidence',
        )
    require(not any(p.is_symlink() for p in (out, *out.parents)), 'Symlink output forbidden')
    before = verify_packet(packet, private_index)
    cases = json.loads((packet / 'cases.json').read_text())['cases']
    links = json.loads(private_index.read_text())['case_linkage']
    ids = [c['case_id'] for c in cases]
    require(len(ids) == len(set(ids)) == 111, 'Exactly the existing 111 cases required')
    lineage = {
        (r['coordinator_page_label'], r['printed_measure_candidate']): r['case_id'] for r in links
    }
    require(
        len(links) == len(lineage) == 111 and set(lineage.values()) == set(ids),
        'Invalid private linkage',
    )
    require(set(lineage) == {(p, n) for p in PILOT for n in range(1, 38)}, 'Incomplete pages')
    selected = {lineage[(page, n)] for page, ns in PILOT.items() for n in ns}
    schedule = {
        'version': 'gt03-workflow-pilot/1',
        'packet_cases_sha256': sha(packet / 'cases.json'),
        'priority_case_ids': [i for i in ids if i in selected],
        'all_case_ids': ids,
        'instructions': 'Use the unchanged GT-02 packet and separate full A/B working forms. '
        'Work priority cases first; leave all unworked observations PENDING. '
        'Transcribe ink independently; UNKNOWN is valid. Do not seek a particular '
        'error or agreement. All 111 cases remain available. The schedule is a '
        'curated workflow pilot, not a representative accuracy sample.',
    }
    out.mkdir(parents=True)
    dump(out / 'reader-schedule.json', schedule)
    dump(
        out / 'custodian-only.json',
        {
            'distribution': 'PRIVATE; never give to readers',
            'packet_sha256': sha(private_index),
            'requested_coverage': PILOT,
            'pilot_cases': len(selected),
            'actual_independent_labels': 0,
            'raw_exports': 'Store immutable originals outside packet; hash each separately. '
            'Do not compare until A and B both frozen. Separate adjudicator required.',
            'pilot_validation': 'GT-02 full submission validator requires all 111 cases completed. '
            'A pilot with PENDING cases is a workflow receipt only, never accepted '
            'ground truth. Preserve the full original export, including PENDING.',
        },
    )
    require(verify_packet(packet, private_index) == before, 'GT-02 packet changed')
    return schedule


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--private-index', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.packet, args.private_index, args.out)
    print(
        json.dumps(
            {
                'pilot_cases': len(result['priority_case_ids']),
                'all_cases': 111,
                'actual_independent_labels': 0,
            }
        )
    )


if __name__ == '__main__':
    main()
