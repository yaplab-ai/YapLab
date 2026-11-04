"""Offline checks: .venv/bin/python verify_recorded_live_review.py"""
from __future__ import annotations

import copy
import hashlib
import html
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

SCRIPT = Path(__file__).parent / 'scripts' / 'export_recorded_live_review.py'
spec = importlib.util.spec_from_file_location('recorded_review', SCRIPT)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class InspectHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.attributes = []
        self.hrefs = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend(attrs)
        self.hrefs.extend(value for key, value in attrs if key == 'href')


class RecordedReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = review.DEFAULT_INPUT.read_bytes()
        cls.document = json.loads(cls.raw)
        cls.sha = hashlib.sha256(cls.raw).hexdigest()

    def test_recorded_counts_statuses_ids_sources_and_usage(self):
        d = self.document
        page = review.render(d, self.sha)
        parser = InspectHTML()
        parser.feed(page)
        self.assertEqual(len(d['snapshots']), 9)
        self.assertEqual(sum(len(s['roles']) for s in d['snapshots']), 27)
        self.assertEqual(parser.tags.count('details'), 27)
        self.assertEqual(parser.tags.count('table'), 2)
        self.assertEqual(parser.tags.count('tr'), 38)  # two headers, nine snapshots, 27 events
        self.assertIn('24 / 27', page)
        self.assertIn('6 / 9', page)
        self.assertIn('27 / 27', page)
        self.assertIn(self.sha, page)
        self.assertIn('b4394bd', page)
        self.assertIn('2026-11-04.3', page)
        self.assertIn('protocol 2', page)
        issues = []
        for snapshot in d['snapshots']:
            for role in snapshot['roles']:
                if role['status'] != 'completed':
                    issues.append(role['validation_issue'])
                    self.assertIn(html.escape(role['validation_issue']), page)
                    self.assertIn(html.escape(role['reason']), page)
                for proposal in role['proposals']:
                    for value in [proposal['action_id'], *proposal['fact_ids'], *proposal['source_ids']]:
                        self.assertIn(html.escape(value), page)
                for source in role['evidence']:
                    self.assertIn(html.escape(source['title']), page)
                    self.assertIn(source['url'], parser.hrefs)
                    self.assertIn(html.escape(source['scope']), page)
                    self.assertIn(html.escape(source['summary']), page)
                    for limit in source['limitations']:
                        self.assertIn(html.escape(limit), page)
            for item in snapshot['plan']:
                self.assertIn(html.escape(item['action_id']), page)
                self.assertIn(html.escape(item['status']), page)
        self.assertCountEqual(issues, ['duplicate_action_ids', 'schema_limits', 'unknown_source_id'])
        self.assertEqual(len(d['usage']), 27)
        self.assertIn('Raw rejected outputs are unavailable', page)
        self.assertIn('source-fit review and known weak matches', page)
        self.assertIn('not a semantic, legal, accessibility, or learning score', page)

    def test_no_active_content_or_external_assets_and_escape_hostile_text(self):
        document = copy.deepcopy(self.document)
        evidence = document['snapshots'][0]['roles'][0]['evidence'][0]
        evidence['title'] = '<script>alert("x")</script>'
        evidence['url'] = 'javascript:alert(1)'
        evidence['scope'] = '<img src=x onerror=alert(2)>'
        evidence['summary'] = '<script>malicious summary</script>'
        evidence['source_locator'] = '<em>historical locator</em>'
        evidence['verification'] = '<svg onload=bad()>'
        document['snapshots'][0]['roles'][0]['proposals'][0]['action_id'] = '</code><script>bad()</script>'
        page = review.render(document, self.sha)
        parser = InspectHTML()
        parser.feed(page)
        for tag in ('script', 'link', 'iframe', 'object', 'embed', 'form', 'img', 'video', 'audio'):
            self.assertNotIn(tag, parser.tags)
        self.assertFalse(any(key.lower().startswith('on') for key, _ in parser.attributes))
        self.assertFalse(any(href and href.lower().startswith('javascript:') for href in parser.hrefs))
        self.assertIn('&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;', page)
        self.assertIn('&lt;img src=x onerror=alert(2)&gt;', page)
        self.assertIn('&lt;script&gt;malicious summary&lt;/script&gt;', page)
        self.assertIn('&lt;em&gt;historical locator&lt;/em&gt;', page)
        self.assertIn('&lt;svg onload=bad()&gt;', page)
        self.assertIn('Content-Security-Policy', page)
        self.assertNotIn('<script>bad()</script>', page)

    def test_generator_is_deterministic_check_detects_drift_and_input_is_unchanged(self):
        with tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve()) as temp:
            source, output = Path(temp) / 'input.json', Path(temp) / 'review.html'
            source.write_bytes(self.raw)
            command = [sys.executable, '-B', str(SCRIPT), '--input', str(source), '--output', str(output)]
            subprocess.run(command, check=True, capture_output=True)
            first = output.read_bytes()
            subprocess.run(command + ['--check'], check=True, capture_output=True)
            subprocess.run(command, check=True, capture_output=True)
            self.assertEqual(output.read_bytes(), first)
            output.write_text('drift', encoding='utf-8')
            self.assertNotEqual(subprocess.run(command + ['--check'], capture_output=True).returncode, 0)
            self.assertEqual(source.read_bytes(), self.raw)
            same = [sys.executable, '-B', str(SCRIPT), '--input', str(source), '--output', str(source)]
            self.assertNotEqual(subprocess.run(same, capture_output=True).returncode, 0)
            self.assertEqual(source.read_bytes(), self.raw)


if __name__ == '__main__':
    unittest.main()
