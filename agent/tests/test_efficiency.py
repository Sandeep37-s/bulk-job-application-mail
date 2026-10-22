import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from jobagent import db, llm


class EfficiencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(db, 'DB_PATH', Path(self.tmp.name) / 'test.db')
        self.db_patch.start()
        self.results = [dict(title='Hiring', url='https://acme.ai/jobs', snippet='AI engineer')]

    def tearDown(self):
        self.db_patch.stop()
        self.tmp.cleanup()

    def test_identical_input_reuses_result_changed_content_calls_again(self):
        with patch.object(llm, 'ask_json', return_value={'companies': [{'company': 'Acme'}]}) as ask:
            self.assertEqual(llm.extract_companies(self.results), [{'company': 'Acme'}])
            self.assertEqual(llm.extract_companies(self.results), [{'company': 'Acme'}])
            self.assertEqual(ask.call_count, 1)
            self.results[0]['snippet'] = 'New AI job, apply hr@acme.ai'
            llm.extract_companies(self.results)
            self.assertEqual(ask.call_count, 2)
        self.assertEqual(db.ai_usage_today()['cache_hits'], 1)

    def test_expired_cache_and_changed_model_are_not_reused(self):
        with patch.object(llm, 'ask_json', return_value={'companies': []}) as ask:
            llm.extract_companies(self.results)
            with db.conn() as c:
                c.execute("UPDATE extraction_cache SET expires='2020-01-01'")
            llm.extract_companies(self.results)
            with patch.object(llm, '_model', 'different-deployment'):
                llm.extract_companies(self.results)
            self.assertEqual(ask.call_count, 3)

    def test_invalid_responses_are_not_cached(self):
        with patch.object(llm, 'ask_json', return_value={'companies': 'invalid'}) as ask:
            for _ in range(2):
                with self.assertLogs('jobagent.llm', level='WARNING'), self.assertRaises(ValueError):
                    llm.extract_companies(self.results)
            self.assertEqual(ask.call_count, 2)

    def test_usage_counts_actual_responses(self):
        response = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 20
        response.choices[0].message.content = '{"companies": []}'
        with patch.object(llm._client.chat.completions, 'create', return_value=response):
            llm.ask_json('system', 'user')
            llm.ask_json('system', 'user')
        usage = db.ai_usage_today()
        self.assertEqual((usage['calls'], usage['input_tokens'], usage['output_tokens']), (2, 200, 40))


if __name__ == '__main__':
    unittest.main()
