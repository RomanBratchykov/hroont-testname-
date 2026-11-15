"""Exercise the runner's tool boundary without requiring a local model."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[3] / 'scripts' / 'ollama_dashboard.py'


class OllamaDashboardTests(unittest.TestCase):
    def runner(self):
        self.assertTrue(SCRIPT.exists(), 'Ollama dashboard runner is missing')
        spec = importlib.util.spec_from_file_location('ollama_dashboard', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_tool_results_return_to_model_and_transcript_is_saved(self):
        runner = self.runner()
        with tempfile.TemporaryDirectory() as temp:
            replies = iter([
                {'role': 'assistant', 'tool_calls': [{'function': {
                    'name': 'agro_analyze', 'arguments': {'request_id': 'stored'}}}]},
                {'role': 'assistant', 'content': 'Coverage is incomplete.'},
            ])
            requests = []
            def chat(body, **kwargs):
                requests.append(body)
                return next(replies)
            with patch.object(runner, 'chat', side_effect=chat), patch.object(
                runner, 'invoke', return_value={'annual_rainfall': None}
            ):
                result = runner.run('Analyze stored data', 'test-model', Path(temp), 'test.db')
            self.assertEqual(result['answer'], 'Coverage is incomplete.')
            self.assertEqual(requests[1]['messages'][-1]['role'], 'tool')
            self.assertIn('null', requests[1]['messages'][-1]['content'])
            self.assertTrue((Path(temp) / 'trace.jsonl').is_file())
            self.assertEqual(result['status'], 'completed')
            dashboard = Path(result['dashboard'])
            self.assertTrue(dashboard.is_file())
            self.assertIn('Coverage is incomplete.', dashboard.read_text())
            self.assertIn('Execution timeline', dashboard.read_text())

    def test_unlisted_tool_never_executes(self):
        runner = self.runner()
        with tempfile.TemporaryDirectory() as temp, patch.object(runner, 'chat', return_value={
            'role': 'assistant', 'tool_calls': [{'function': {'name': 'shell', 'arguments': {}}}]
        }), patch.object(runner, 'invoke') as invoke:
            with self.assertRaisesRegex(ValueError, 'not allowed'):
                runner.run('Create dashboard', 'test-model', Path(temp), 'test.db')
            invoke.assert_not_called()
            self.assertIn('Failed', (Path(temp) / 'run-dashboard.html').read_text())

    def test_loop_limit_is_an_error(self):
        runner = self.runner()
        with tempfile.TemporaryDirectory() as temp, patch.object(runner, 'chat', return_value={
            'role': 'assistant', 'tool_calls': [{'function': {'name': 'agro_analyze', 'arguments': {'request_id': 'x'}}}]
        }), patch.object(runner, 'invoke', return_value={}):
            with self.assertRaisesRegex(ValueError, 'limit'):
                runner.run('Analyze', 'test-model', Path(temp), 'test.db', max_steps=1)
