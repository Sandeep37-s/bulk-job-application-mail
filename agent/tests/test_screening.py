import unittest
from unittest.mock import patch
import test_sending
from jobagent import db, screening, sending


class ScreeningTests(unittest.TestCase):
    setUp = test_sending.SendingTests.setUp
    tearDown = test_sending.SendingTests.tearDown

    def test_experience_rules(self):
        ok = [('AI Engineer', None), ('AI Engineer', '0-2 years of experience'), ('ML Engineer', '2+ years'),
              ('AI Engineer', 'Freshers can apply'), ('Junior ML Engineer', '1-3 yrs'), ('GenAI Engineer', '1.5 years')]
        skip = [('AI Engineer', '3-5 years of experience'), ('ML Engineer', '5+ years'), ('AI Engineer', 'Minimum 4 yrs'),
                ('Senior AI Engineer', None), ('Sr. ML Engineer', None), ('Lead Data Scientist', None),
                ('Principal ML Engineer', None), ('Staff AI Engineer', None), ('AI Engineering Manager', None)]
        for role, text in ok:
            self.assertIsNone(screening.experience_reason(role, text), (role, text))
        for role, text in skip:
            self.assertIsNotNone(screening.experience_reason(role, text), (role, text))

    def test_experience_quote_must_be_in_source(self):
        results = [dict(url='https://linkedin.com/posts/x', title='Hiring AI Engineer', snippet='We need 0-1 years')]
        company = dict(source_url='https://linkedin.com/posts/x', experience_text='5+ years')
        self.assertIsNone(screening.verified_experience(company, results))  # invented quote ignored
        company['experience_text'] = '0-1 years'
        self.assertEqual(screening.verified_experience(company, results), '0-1 years')

    def test_fake_posts(self):
        fake = ['Registration fee of Rs 2000 required', 'Pay 1500 before joining for the kit',
                'Guaranteed job after training', 'No interview! Earn 5000 per day', 'Apply on WhatsApp only',
                'Refundable security deposit of ₹3000']
        real = ['Hiring AI Engineer, send CV to careers@acme.ai', 'Share resume on WhatsApp or email jobs@acme.ai',
                'Fee-free hiring drive for ML engineers']
        for text in fake:
            self.assertIsNotNone(screening.scam_reason(dict(source_url='u'), [dict(url='u', snippet=text)]), text)
        for text in real:
            self.assertIsNone(screening.scam_reason(dict(source_url='u'), [dict(url='u', snippet=text)]), text)

    def test_queued_senior_role_skipped_at_send(self):
        db.update_lead(self.lead, hiring_role='Senior AI Engineer')
        with patch.object(sending, 'send_email') as smtp:
            self.assertIn('Skipped', sending.send_one(self.lead))
            smtp.assert_not_called()
        self.assertEqual(db.get_lead(self.lead)['status'], 'skipped_experience')

    def test_queued_years_skipped_at_send(self):
        db.kv_set(f'experience:{self.lead}', '4+ years')
        with patch.object(sending, 'send_email') as smtp:
            self.assertIn('Skipped', sending.send_one(self.lead))
            smtp.assert_not_called()

    def test_personal_email_held_until_approved(self):
        db.update_lead(self.lead, email='acme.hiring@gmail.com')
        with patch.object(sending, 'send_email') as smtp:
            self.assertIn('Held', sending.send_one(self.lead))
            smtp.assert_not_called()
            self.assertNotIn(self.lead, [l['id'] for l in sending.pending_queue()])
            db.kv_set(f'approved:{self.lead}', '1')
            db.kv_set(f'auto_eligible:{self.lead}', '1')
            self.assertTrue(sending.send_one(self.lead).startswith('Sent to'))


if __name__ == '__main__':
    unittest.main()
