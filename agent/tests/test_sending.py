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


if __name__ == '__main__':
    unittest.main()
