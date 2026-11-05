"""Prepare deterministic, local notebook inputs from curated policy notes.

Whitespace normalization and chunking are adapted from ITUAIReadiness's
"Colab Free Tier LLM Notebook.ipynb", pinned at the commit below.

MIT License; Copyright (c) 2026 Vishnu Ram OV.
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from __future__ import annotations

import hashlib
import json
import re
from importlib import resources
from pathlib import Path

from .evidence import Corpus, load_corpus

NOTEBOOK_URL = 'https://github.com/CrashingGuru/ITUAIReadiness'
NOTEBOOK_COMMIT = '84010da9e9c443afcceeccb86d1700a662223395'
MIT_NOTICE = '''MIT License

Copyright (c) 2026 Vishnu Ram OV

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.'''
RIGHTS_CAVEAT = ('Curated summaries and selected attributed source text have separate rights. '
                 'Consult each source, locator and recorded reuse terms before reuse.')
_SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')


def normalize_text(text: str) -> str:
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[^\S\n]+', ' ', text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120,
               min_chunk_chars: int = 80) -> list[str]:
    """Match the pinned notebook's Cell 8, including its boundary behavior."""
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size or min_chunk_chars < 0:
        raise ValueError('invalid chunk configuration')
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        if end < n:
            ws = text.rfind(' ', start + int(chunk_size * 0.9), end)
            if ws != -1:
                end = ws
        chunk = text[start:end].strip()
        if len(chunk) >= min_chunk_chars:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def _source_text(source) -> str | None:
    path = getattr(source, 'text_path', None)
    if not path:
        return None
    if not re.fullmatch(r'source_texts/[a-z0-9]+(?:-[a-z0-9]+)*\.txt', path):
        raise ValueError(f'unsafe source text path: {path!r}')
    data = resources.files('frontrow.policy').joinpath(*path.split('/')).read_bytes()
    if hashlib.sha256(data).hexdigest() != getattr(source, 'text_sha256', None):
        raise ValueError(f'source text hash mismatch: {source.id}')
    if not all(getattr(source, name, None) for name in ('text_retrieved', 'text_locator', 'text_rights', 'text_status')):
        raise ValueError(f'incomplete source text provenance: {source.id}')
    return data.decode('utf-8')


def _document(source) -> str:
    lines = [f'# {source.title}', '', 'Original curated summary with any selected source text labelled below.',
             RIGHTS_CAVEAT, '', f'Source ID: {source.id}', f'Authority: {source.authority}',
             f'URL: {source.url}', f'Jurisdiction: {source.jurisdiction}',
             f'Institution: {source.institution or "general"}',
             f'Document type: {source.document_type}', f'Published: {source.published}',
             f'Retrieved: {source.retrieved}', f'Source locator: {source.source_locator}',
             '', '## Scope', source.scope, '', '## Summary', source.summary,
             '', '## Considerations']
    lines.extend(f'- {item}' for item in source.requirements)
    lines.extend(['', '## Limitations'])
    lines.extend(f'- {item}' for item in source.limitations)
    reuse_note = getattr(source, 'reuse_note', None)
    if reuse_note:
        lines.extend(['', '## Source rights and reuse', str(reuse_note)])
    source_text = _source_text(source)
    if source_text is not None:
        lines.extend(['', '## Selected source text',
                      f'Status: {source.text_status}', f'Locator: {source.text_locator}',
                      f'Retrieved: {source.text_retrieved}', f'Rights: {source.text_rights}',
                      f'SHA-256 of source text asset: {source.text_sha256}', '', source_text.rstrip()])
    return '\n'.join(lines) + '\n'


def build_bundle(corpus: Corpus | None = None, *, institution: str = 'general') -> dict[str, bytes]:
    """Build paths relative to the output root, without writing or network access."""
    if institution not in ('general', 'uaeu'):
        raise ValueError(f'unsupported institution: {institution!r}')
    corpus = corpus if corpus is not None else load_corpus()
    selected = [source for source in corpus.entries
                if source.institution in (None, 'general') or source.institution == institution]
    if not selected:
        raise ValueError('corpus has no entries in the selected institution scope')
    files: dict[str, bytes] = {}
    provenance = {}
    chunks = []
    for source in sorted(selected, key=lambda item: item.id):
        if not _SLUG.fullmatch(source.id):
            raise ValueError(f'unsafe source ID: {source.id!r}')
        filename = source.id + '.md'
        if filename in provenance:
            raise ValueError(f'duplicate source ID: {source.id!r}')
        doc = _document(source).encode('utf-8')
        source_chunks = chunk_text(normalize_text(doc.decode('utf-8')))
        if not source_chunks:
            raise ValueError(f'no notebook chunks for source: {source.id!r}')
        files['docs/' + filename] = doc
        provenance[filename] = {
            'id': source.id, 'title': source.title, 'url': source.url,
            'authority': source.authority, 'scope': source.scope,
            'document_type': source.document_type, 'jurisdiction': source.jurisdiction,
            'institution': source.institution or 'general',
            'published': source.published, 'retrieved': source.retrieved,
            'sha256': hashlib.sha256(doc).hexdigest(),
            'content_status': getattr(source, 'text_status', None) or 'original_curated_summary_not_full_text',
            'text_path': getattr(source, 'text_path', None),
            'text_sha256': getattr(source, 'text_sha256', None),
            'text_retrieved': getattr(source, 'text_retrieved', None),
            'text_locator': getattr(source, 'text_locator', None),
            'text_rights': getattr(source, 'text_rights', None),
            'reuse_note': getattr(source, 'reuse_note', None),
            'verification': getattr(source, 'verification', None),
            'rights_caveat': RIGHTS_CAVEAT,
        }
        chunks.extend({'source': filename, 'chunk_id': i, 'text': chunk}
                      for i, chunk in enumerate(source_chunks))
    manifest = {
        'institution': institution,
        'scope_warning': ('General sources only; applicability depends on the institution, jurisdiction and activity.'
                          if institution == 'general' else
                          'Includes UAEU-specific sources alongside general sources; UAEU-specific material does not automatically apply to other institutions.'),
        'status': 'local_notebook_input_prepared',
        'hosted_import_verified': False, 'embedding_index_built': False,
        'corpus_version': corpus.version, 'corpus_limitations': corpus.limitations,
        'content_status': 'curated_summaries_and_selected_source_text',
        'rights_caveat': RIGHTS_CAVEAT,
        'notebook_reference': {'repository': NOTEBOOK_URL, 'commit': NOTEBOOK_COMMIT,
                               'file': 'Colab Free Tier LLM Notebook.ipynb',
                               'cell': 'Cell 8 - Parse, clean, and chunk documents',
                               'chunk_size': 800, 'chunk_overlap': 120,
                               'min_chunk_chars': 80, 'license_notice': MIT_NOTICE},
        'sources': provenance,
    }
    files['manifest.json'] = _json_bytes(manifest)
    files['chunks.jsonl'] = ''.join(json.dumps(c, ensure_ascii=False, separators=(',', ':')) + '\n'
                                    for c in chunks).encode('utf-8')
    return files


def _reject_symlink_components(path: Path) -> None:
    absolute = path.absolute()
    for component in (absolute, *absolute.parents):
        if component.is_symlink():
            raise ValueError(f'symlink in output path: {component}')


def export_bundle(output: Path, *, check: bool = False, corpus: Corpus | None = None,
                  institution: str = 'general') -> None:
    """Write a fresh bundle or verify exact existing files; never follow symlinks."""
    output = Path(output)
    _reject_symlink_components(output)
    expected = build_bundle(corpus, institution=institution)
    if check:
        if not output.is_dir():
            raise ValueError('output bundle does not exist')
        actual = set()
        for path in output.rglob('*'):
            if path.is_symlink():
                raise ValueError(f'symlink in output bundle: {path}')
            if path.is_file():
                actual.add(path.relative_to(output).as_posix())
            elif path.is_dir():
                if path.relative_to(output).as_posix() != 'docs':
                    raise ValueError(f'unexpected output directory: {path}')
            else:
                raise ValueError(f'unsupported output entry: {path}')
        if actual != set(expected):
            raise ValueError('bundle files differ from expected output')
        for name, data in expected.items():
            if (output / name).read_bytes() != data:
                raise ValueError(f'bundle content differs: {name}')
        return
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('output exists and is not an empty directory')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'docs').mkdir()
    for name, data in expected.items():
        with (output / name).open('xb') as stream:
            stream.write(data)
