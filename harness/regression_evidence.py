"""Interpret actual pytest JUnit evidence without waiving failures or skips."""
import xml.etree.ElementTree as ET
from pathlib import Path
from .policy import digest


def summarize(path: Path, exit_code: int):
    root = ET.parse(path).getroot()
    cases = list(root.iter('testcase'))
    skipped = [{'name': c.get('name'), 'reason': c.find('skipped').get('message', '')}
               for c in cases if c.find('skipped') is not None]
    failures = sum(c.find('failure') is not None for c in cases)
    errors = sum(c.find('error') is not None for c in cases)
    passed = len(cases) - len(skipped) - failures - errors
    return {'exit_code': exit_code, 'test_cases': len(cases), 'passed': passed,
            'failures': failures, 'errors': errors, 'skipped': skipped, 'junit_sha256': digest(path),
            'mandatory_gate': 'PASS' if cases and exit_code == 0 and not skipped and not failures and not errors else 'BLOCKED'}
