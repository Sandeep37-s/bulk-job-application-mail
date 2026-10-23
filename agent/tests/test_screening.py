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


    def test_negated_fee_is_not_a_scam(self):
        for text in ['There is no registration fee', 'We never charge any training fee', 'Zero joining fee']:
            self.assertIsNone(screening.scam_reason(dict(source_url='u'), [dict(url='u', snippet=text)]), text)
        self.assertIsNotNone(screening.scam_reason(dict(source_url='u'), [dict(url='u', snippet='No experience needed. Registration fee 500')]))

    def test_years_in_title_and_extra_senior_words(self):
        self.assertIsNotNone(screening.experience_reason('AI Engineer (5+ years)', None))
        self.assertIsNone(screening.experience_reason('Data Scientist (2-4 Years Experience)', None))
        for title in ['AI Architect', 'Head of AI', 'Director, Machine Learning', 'VP AI Engineering']:
            self.assertIsNotNone(screening.experience_reason(title, None), title)

    def test_agencies(self):
        for name in ['Jobaaj Com', 'Teamware Solutions', 'XYZ Staffing', 'Quick Placements', 'Talent Solutions Pvt']:
            self.assertTrue(screening.is_agency(name), name)
        for name in ['Acme AI', 'Vira AI : Agentic AI for HR', 'CoffeeBeans Consulting']:
            self.assertFalse(screening.is_agency(name), name)
        db.update_lead(self.lead, company='Teamware Solutions')
        with patch.object(sending, 'send_email') as smtp:
            self.assertIn('agency', sending.send_one(self.lead))
            smtp.assert_not_called()

    def test_duplicate_and_ineligible_leave_queue(self):
        db.add_lead(domain='old.ai', email='hr@acme.ai', status='sent', sent_at=db.now())
        with patch.object(sending, 'send_email') as smtp:
            sending.send_one(self.lead)
            smtp.assert_not_called()
        self.assertEqual(db.get_lead(self.lead)['status'], 'duplicate')
        other = db.add_lead(domain='x.ai', email='hr@x.ai', hiring_role='Sales Executive', email_source='s',
                            subject='s', body='b', status='pending')
        db.kv_set(f'auto_eligible:{other}', '1')
        db.kv_set(f'deadline_scanned:{other}', '1')
        sending.send_one(other)
        self.assertEqual(sending.pending_queue(), [])

    def test_refresh_only_sendable_and_never_stalls(self):
        from jobagent import deadlines
        db.update_lead(self.lead, job_url='https://acme.ai/jobs')
        db.kv_set(f'deadline_scanned:{self.lead}', '0')
        legacy = db.add_lead(domain='legacy.ai', hiring_role='AI Engineer', job_url='https://legacy.ai/jobs', status='pending')
        fetched = []
        def fake_fetch(results, chars):
            fetched.append(results[0]['url'])
            return [dict(results[0], snippet='')]  # blocked page
        with patch('jobagent.search.with_page_text', fake_fetch), patch('jobagent.llm.extract_companies') as llm:
            deadlines.refresh_pending_deadlines()
            llm.assert_not_called()
        self.assertEqual(fetched, ['https://acme.ai/jobs'])
        self.assertEqual(db.kv_get(f'deadline_scanned:{self.lead}'), '1')

    def test_retry_rotates_and_skips_unvalidated(self):
        from jobagent import pipeline
        old = db.add_lead(domain='old.ai', company='Old AI', status='no_contact')
        new = db.add_lead(domain='new.ai', company='New AI', status='no_contact', hiring_role='AI Engineer')
        db.kv_set(f'validated:{new}', '1')
        with db.conn() as c:
            c.execute("UPDATE leads SET updated='2000-01-01T00:00:00+00:00' WHERE id IN (?, ?)", (old, new))
        with patch.object(pipeline, 'process_company', return_value=None) as proc, \
             patch.object(pipeline, 'queries', return_value=[]):
            pipeline.run_cycle()
        self.assertEqual([call.args[0]['id'] for call in proc.call_args_list], [new])
        self.assertTrue(proc.call_args.kwargs['retry'])
        self.assertEqual(db.retry_candidates(), [])  # both bumped, not stuck at the front

    def test_retry_kind_without_results(self):
        from jobagent import pipeline
        company = dict(company='New AI', website='new.ai', city='Noida', is_ai_company=True, est_employees=20,
                       hiring_role='Senior AI Engineer')
        with patch.object(pipeline, 'scrape_site') as scrape:
            self.assertIsNone(pipeline.process_company(company, retry=True))
            scrape.assert_not_called()


if __name__ == '__main__':
    unittest.main()
