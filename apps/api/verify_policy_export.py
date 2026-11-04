"""Offline notebook-compatible export checks: .venv/bin/python verify_policy_export.py"""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from frontrow.policy.evidence import Corpus, load_corpus
from frontrow.policy.export import build_bundle, chunk_text, export_bundle, normalize_text


class PolicyExportTests(unittest.TestCase):
    def setUp(self):
        # Resolve system temporary directories such as /tmp when they are symlinks.
        self.temp = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve())
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.corpus = load_corpus()

    def test_notebook_chunk_fixture_and_normalization(self):
        self.assertEqual(normalize_text('  one\r\n\r\n\r\ntwo\t  words  '), 'one\n\ntwo words')
        text = 'abcdefghijklmnopqr stuvwxyz0123456789 ABCDEFGHIJ'
        self.assertEqual(chunk_text(text, 20, 5, 1), [
            'abcdefghijklmnopqr', 'nopqr stuvwxyz012345', '123456789 ABCDEFGHIJ',
        ])
        self.assertEqual(chunk_text('tiny', 20, 5, 80), [])

    def test_deterministic_documents_chunks_and_provenance(self):
        one, two = self.base / 'one', self.base / 'two'
        export_bundle(one, corpus=self.corpus)
        export_bundle(two, corpus=self.corpus)
        first = {p.relative_to(one): p.read_bytes() for p in one.rglob('*') if p.is_file()}
        second = {p.relative_to(two): p.read_bytes() for p in two.rglob('*') if p.is_file()}
        self.assertEqual(first, second)
        manifest = json.loads(first[Path('manifest.json')])
        self.assertEqual(manifest['status'], 'local_notebook_input_prepared')
        self.assertFalse(manifest['hosted_import_verified'])
        self.assertFalse(manifest['embedding_index_built'])
        self.assertEqual(manifest['institution'], 'general')
        self.assertTrue(manifest['scope_warning'])
        self.assertEqual(set(manifest['sources']), {s.id + '.md' for s in self.corpus.entries
                                                   if s.institution in (None, 'general')})
        for name, source in manifest['sources'].items():
            self.assertEqual(source['sha256'], hashlib.sha256(first[Path('docs') / name]).hexdigest())
            self.assertEqual(source['content_status'], 'original_curated_summary_not_full_text')
        records = [json.loads(line) for line in first[Path('chunks.jsonl')].splitlines()]
        self.assertTrue(records)
        self.assertEqual({r['source'] for r in records}, set(manifest['sources']))
        for name in manifest['sources']:
            document = first[Path('docs') / name].decode('utf-8')
            expected = chunk_text(normalize_text(document))
            actual = [r for r in records if r['source'] == name]
            self.assertEqual(actual, [{'source': name, 'chunk_id': i, 'text': text}
                                      for i, text in enumerate(expected)])
        export_bundle(one, check=True, corpus=self.corpus)
        (one / 'chunks.jsonl').write_text('drift', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'differs'):
            export_bundle(one, check=True, corpus=self.corpus)

    def test_institution_scope_and_scope_aware_check(self):
        general = build_bundle(self.corpus)
        uaeu = build_bundle(self.corpus, institution='uaeu')
        self.assertEqual(uaeu, build_bundle(self.corpus, institution='uaeu'))
        general_manifest = json.loads(general['manifest.json'])
        uaeu_manifest = json.loads(uaeu['manifest.json'])
        self.assertEqual(uaeu_manifest['institution'], 'uaeu')
        self.assertIn('other institutions', uaeu_manifest['scope_warning'])
        general_names = set(general_manifest['sources'])
        uaeu_names = set(uaeu_manifest['sources'])
        expected_uaeu = {s.id + '.md' for s in self.corpus.entries if s.institution == 'uaeu'}
        self.assertTrue(expected_uaeu)
        self.assertEqual(uaeu_names, general_names | expected_uaeu)
        self.assertFalse(general_names & expected_uaeu)
        for name in uaeu_names:
            source = uaeu_manifest['sources'][name]
            self.assertEqual(source['sha256'], hashlib.sha256(uaeu['docs/' + name]).hexdigest())
            self.assertIn(f"Institution: {source['institution']}", uaeu['docs/' + name].decode())
        for bundle, names in ((general, general_names), (uaeu, uaeu_names)):
            records = [json.loads(line) for line in bundle['chunks.jsonl'].splitlines()]
            self.assertEqual({record['source'] for record in records}, names)
        output = self.base / 'uaeu'
        export_bundle(output, corpus=self.corpus, institution='uaeu')
        export_bundle(output, check=True, corpus=self.corpus, institution='uaeu')
        with self.assertRaises(ValueError):
            export_bundle(output, check=True, corpus=self.corpus)
        with self.assertRaises(ValueError):
            build_bundle(self.corpus, institution='unknown')

    def test_rejects_unsafe_ids_empty_corpus_and_duplicates(self):
        source = self.corpus.entries[0]
        for bad in ('../outside', 'UPPER', 'foo.md', 'a/b', 'a--b'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                build_bundle(self.corpus.model_copy(update={'entries': [source.model_copy(update={'id': bad})]}))
        with self.assertRaises(ValueError):
            build_bundle(self.corpus.model_copy(update={'entries': []}))
        with self.assertRaises(ValueError):
            build_bundle(self.corpus.model_copy(update={'entries': [source, source]}))

    def test_existing_nonempty_and_symlinks_rejected(self):
        output = self.base / 'existing'
        output.mkdir()
        (output / 'keep').write_text('important')
        with self.assertRaises(ValueError):
            export_bundle(output, corpus=self.corpus)
        self.assertEqual((output / 'keep').read_text(), 'important')
        link = self.base / 'link'
        link.symlink_to(output, target_is_directory=True)
        for check in (False, True):
            with self.subTest(check=check), self.assertRaises(ValueError):
                export_bundle(link, check=check, corpus=self.corpus)
        fresh = self.base / 'fresh'
        export_bundle(fresh, corpus=self.corpus)
        (fresh / 'docs' / 'rogue.md').symlink_to(output / 'keep')
        with self.assertRaises(ValueError):
            export_bundle(fresh, check=True, corpus=self.corpus)

    def test_check_rejects_missing_extra_or_empty_content(self):
        output = self.base / 'bundle'
        with self.assertRaises(ValueError):
            export_bundle(output, check=True, corpus=self.corpus)
        export_bundle(output, corpus=self.corpus)
        (output / 'docs' / 'extra.md').write_text('extra')
        with self.assertRaises(ValueError):
            export_bundle(output, check=True, corpus=self.corpus)
        (output / 'docs' / 'extra.md').unlink()
        (output / 'chunks.jsonl').write_text('')
        with self.assertRaises(ValueError):
            export_bundle(output, check=True, corpus=self.corpus)


if __name__ == '__main__':
    unittest.main()
