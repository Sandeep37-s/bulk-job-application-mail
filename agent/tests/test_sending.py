import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from jobagent import db, sending


class SendingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = patch.object(db, 'DB_PATH', Path(self.tmp.name) / 'db.sqlite')
        self.p.start()
        self.lead = db.add_lead(domain='acme.ai', email='hr@acme.ai', hiring_role='AI Engineer',
                                email_source='https://acme.ai/jobs', subject='Application', body='Hello', status='pending')
        db.kv_set(f'auto_eligible:{self.lead}', '1')

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def test_roles(self):
        for title in ['AI Engineer', 'ML Engineer', 'Data Scientist', 'NLP Researcher', 'Computer Vision Engineer', 'MLOps Engineer']:
            self.assertTrue(sending.relevant_role(title), title)
        for title in ['Office staff at AI company', 'AI Sales Engineer', 'HR Manager', 'Software Engineer', '', 'AI Recruitment Specialist']:
            self.assertFalse(sending.relevant_role(title), title)

    def test_send_once(self):
        with patch.object(sending, 'send_email') as smtp:
            self.assertTrue(sending.send_one(self.lead).startswith('Sent to'))
            sending.send_one(self.lead)
            smtp.assert_called_once()

    def test_pause_gap_and_cap(self):
        with patch.object(sending, 'send_email') as smtp:
            db.kv_set('paused', '1')
            sending.send_one(self.lead)
            db.kv_set('paused', '0')
            db.kv_set('last_send_ts', str(sending.time.time()))
            sending.send_one(self.lead)
            db.kv_set('last_send_ts', '0')
            for i in range(40):
                db.add_lead(domain=f'{i}.ai', status='sent', sent_at=db.now())
            self.assertIn('limit', sending.send_one(self.lead))
            smtp.assert_not_called()

    def test_error_halts_sending_without_automatic_retry(self):
        with patch.object(sending, 'send_email', side_effect=TimeoutError('SMTP timeout')) as smtp:
            sending.send_one(self.lead)
            sending.send_one(self.lead)
            smtp.assert_called_once()
        self.assertEqual(db.kv_get('sending_paused'), '1')
        self.assertEqual(db.get_lead(self.lead)['status'], 'send_uncertain')

    def test_old_drafts_not_automatically_sent(self):
        db.kv_set(f'auto_eligible:{self.lead}', '0')
        with patch.object(sending, 'send_email') as smtp:
            sending.send_one(self.lead)
            smtp.assert_not_called()

    def test_source_evidence_required(self):
        company = dict(hiring_role='AI Engineer', source_url='https://acme.ai/jobs')
        self.assertFalse(sending.evidence_matches(company, [dict(url='https://other.ai', title='AI Engineer')]))
        self.assertTrue(sending.evidence_matches(company, [dict(url='https://acme.ai/jobs', title='Hiring AI Engineer')]))

    def test_hiring_precedes_older_company_outreach(self):
        db.update_lead(self.lead, hiring_role=None)
        db.kv_set(f'outreach_kind:{self.lead}', 'company')
        hiring = db.add_lead(domain='new.ai', hiring_role='ML Engineer', status='pending')
        db.kv_set(f'auto_eligible:{hiring}', '1')
        self.assertEqual([x['id'] for x in sending.pending_queue()], [hiring, self.lead])

    def test_fallback_requires_ai_evidence_and_no_unrelated_role(self):
        company = dict(company='Acme', is_ai_company=True, source_url='https://acme.ai')
        results = [dict(url='https://acme.ai', title='Acme builds machine learning products')]
        self.assertEqual(sending.outreach_kind(company, results), 'company')
        company['hiring_role'] = 'Office Staff'
        self.assertIsNone(sending.outreach_kind(company, results))
        company['hiring_role'] = None
        results[0]['title'] = 'Acme office supplies'
        self.assertIsNone(sending.outreach_kind(company, results))

    def test_overflow_stays_pending_and_sends_after_quota_expires(self):
        for i in range(40):
            db.add_lead(domain=f'old{i}.ai', status='sent', sent_at=db.now())
        with patch.object(sending, 'send_email') as smtp:
            self.assertIn('limit', sending.send_one(self.lead))
            self.assertEqual(db.get_lead(self.lead)['status'], 'pending')
            smtp.assert_not_called()
            with db.conn() as c:
                c.execute("UPDATE leads SET sent_at='2020-01-01T00:00:00+00:00' WHERE status='sent'")
            self.assertTrue(sending.send_one(self.lead).startswith('Sent to'))
            smtp.assert_called_once()

    def test_verified_company_inquiry_can_send(self):
        db.update_lead(self.lead, hiring_role=None)
        db.kv_set(f'outreach_kind:{self.lead}', 'company')
        with patch.object(sending, 'send_email') as smtp:
            self.assertIn('company outreach', sending.send_one(self.lead))
            smtp.assert_called_once()


if __name__ == '__main__':
    unittest.main()
