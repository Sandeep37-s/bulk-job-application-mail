import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jobagent import db, pipeline, search


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(db, 'DB_PATH', Path(self.tmp.name) / 'test.db')
        self.db_patch.start()

    def tearDown(self):
        self.db_patch.stop()
        self.tmp.cleanup()

    def test_seen_urls_expire_and_refresh(self):
        db.mark_urls(['https://acme.ai/jobs'])
        self.assertTrue(db.url_seen('https://acme.ai/jobs'))
        with db.conn() as c:
            c.execute("UPDATE seen_urls SET ts='2020-01-01T00:00:00+00:00'")
        self.assertFalse(db.url_seen('https://acme.ai/jobs'))
        db.mark_urls(['https://acme.ai/jobs'])
        self.assertTrue(db.url_seen('https://acme.ai/jobs'))

    def test_retry_only_discovery_failures(self):
        for status, error, allowed in [('no_contact', None, True), ('failed', 'compose: timeout', True),
                                       ('failed', 'SMTP timeout', False), ('sent', None, False),
                                       ('skipped', None, False), ('pending', None, False), ('blocked', None, False)]:
            domain = status + str(allowed) + '.ai'
            lead_id = db.add_lead(domain=domain, status=status, error=error)
            self.assertTrue(db.domain_known(domain))
            with db.conn() as c:
                c.execute("UPDATE leads SET updated='2020-01-01T00:00:00+00:00' WHERE id=?", (lead_id,))
            self.assertEqual(db.domain_known(domain), not allowed)
            retried = db.add_lead(domain=domain, email='hr@acme.ai')
            self.assertEqual(retried, lead_id if allowed else None)
            if not allowed:
                self.assertEqual(db.get_lead(lead_id)['status'], status)

    def test_queries_rotate(self):
        self.assertNotEqual(list(pipeline.queries(0))[:9], list(pipeline.queries(1))[:9])

    def test_pagination_reaches_primary_provider(self):
        with patch('ddgs.DDGS') as ddgs:
            ddgs.return_value.text.return_value = [{'href': 'https://acme.ai'}]
            search._search_ddgs('AI jobs', page=3, timelimit='w')
            self.assertEqual(ddgs.return_value.text.call_args.kwargs['page'], 3)
            self.assertEqual(ddgs.return_value.text.call_args.kwargs['timelimit'], 'w')

    def test_failed_extraction_does_not_consume_urls(self):
        result = dict(url='https://acme.ai/jobs', title='AI jobs', snippet='Hiring')
        with patch.object(pipeline, 'queries', return_value=['AI jobs']), \
             patch.object(pipeline, 'search', return_value=[result]), \
             patch.object(pipeline, 'with_page_text', side_effect=lambda rows: rows), \
             patch.object(pipeline, 'extract_companies', side_effect=RuntimeError('temporary failure')):
            with self.assertLogs('jobagent.pipeline', level='ERROR'):
                self.assertEqual(pipeline.run_cycle(), [])
        self.assertFalse(db.url_seen(result['url']))


if __name__ == '__main__':
    unittest.main()
