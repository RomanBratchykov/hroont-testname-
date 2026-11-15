"""Check visual reports expose observed data without running model-supplied HTML."""
import tempfile
from pathlib import Path

from agrodata import ollama_report


def test_report_shows_flow_and_escapes_model_content():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        artifact = root / 'reports' / 'climate.html'
        artifact.parent.mkdir()
        artifact.write_text('<html>Climate</html>')
        events = [
            {'stage': 'request', 'elapsed_seconds': 0, 'data': {
                'model': 'local-model', 'messages': [{'role': 'user', 'content': '<script>alert(1)</script>'}]}},
            {'stage': 'tool_result', 'elapsed_seconds': 2, 'data': {
                'name': 'agro_dashboard', 'result': {'output': str(artifact),
                    'summary': {'coverage': 0.75, 'precipitation_mm': None}}}},
            {'stage': 'response', 'elapsed_seconds': 3, 'data': {
                'content': 'Some data is missing.', 'role': 'assistant'}},
            {'stage': 'finished', 'elapsed_seconds': 3, 'data': {'status': 'completed'}},
        ]
        path = ollama_report.render(events, root)
        html = path.read_text()
        assert '<script>alert(1)</script>' not in html
        assert '&lt;script&gt;' in html
        assert 'reports/climate.html' in html
        assert '75.0%' in html
        assert 'Not available' in html
        assert 'Some data is missing.' in html
        assert 'local-model' in html
        assert '<svg' in html


def test_report_preserves_errors_and_blocks_external_artifacts():
    with tempfile.TemporaryDirectory() as temp:
        path = ollama_report.render([
            {'stage': 'tool_result', 'data': {'name': 'agro_run', 'result': {
                'status': 'failed', 'error': 'Source unavailable',
                'artifacts': {'dashboard': 'javascript:alert(1)'}}}},
            {'stage': 'error', 'data': 'Ollama timed out'},
        ], Path(temp))
        html = path.read_text()
        assert 'Ollama timed out' in html
        assert 'Source unavailable' in html
        assert 'href="javascript:' not in html
        assert 'Failed' in html
