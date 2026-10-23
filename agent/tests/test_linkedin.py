import unittest
from unittest.mock import patch, MagicMock

from jobagent.contacts import listed_contact
from jobagent.pipeline import process_company, queries
from jobagent.search import with_page_text


POST = 'https://www.linkedin.com/posts/acme_hiring-123'


class LinkedInTests(unittest.TestCase):
    def setUp(self):
        self.company = dict(company='Acme AI', website='acme.ai', city='Noida',
                            is_ai_company=True, est_employees=20,
                            hiring_role='AI Engineer', contact_email='recruiter@gmail.com', source_url=POST, job_url=POST)
        self.results = [dict(url=POST, title='Acme is hiring AI Engineer',
                             snippet='Apply: recruiter@gmail.com')]

    def test_post_queries(self):
        self.assertTrue(any('linkedin.com/posts' in q for q in queries()))
        self.assertTrue(any('linkedin.com/feed/update' in q for q in queries()))

    def test_exact_source_and_email(self):
        self.assertEqual(listed_contact(self.company, self.results), ('recruiter@gmail.com', POST))
        self.results[0]['url'] = 'https://other.ai'
        self.assertEqual(listed_contact(self.company, self.results), (None, None))
        self.results[0]['url'] = POST
        self.results[0]['snippet'] = 'notrecruiter@gmail.com'
        self.assertEqual(listed_contact(self.company, self.results), (None, None))

    def test_invented_email_rejected(self):
        self.results[0]['snippet'] = 'Apply on our website'
        self.assertEqual(listed_contact(self.company, self.results), (None, None))

    def test_snippet_survives_public_page(self):
        response = MagicMock(status_code=200, headers={'content-type': 'text/html'},
                             text='<html><body>' + 'Sign in to LinkedIn. ' * 30 + '</body></html>')
        with patch('jobagent.search.httpx.Client') as client:
            client.return_value.__enter__.return_value.get.return_value = response
            enriched = with_page_text(self.results)
        self.assertIn('recruiter@gmail.com', enriched[0]['snippet'])

    def test_post_contact_preferred_and_draft_pending(self):
        with patch('jobagent.pipeline.db') as db, \
             patch('jobagent.pipeline.scrape_site', return_value=('AI products', ['hr@acme.ai'],
                   {'hr@acme.ai': 'https://acme.ai/careers'})), \
             patch('jobagent.pipeline.compose_email', return_value=('Application', 'Draft')):
            db.domain_known.return_value = False
            db.add_lead.return_value = 42
            self.assertEqual(process_company(self.company, self.results), 42)
            fields = db.add_lead.call_args.kwargs
            self.assertEqual(fields['email'], 'recruiter@gmail.com')
            self.assertEqual(fields['email_source'], POST)
            db.update_lead.assert_called_once_with(42, subject='Application', body='Draft', status='pending')

    def test_no_post_email_keeps_website_contact(self):
        self.results[0]['snippet'] = 'We are hiring'
        with patch('jobagent.pipeline.db') as db, \
             patch('jobagent.pipeline.scrape_site', return_value=('AI', ['hr@acme.ai'],
                   {'hr@acme.ai': 'https://acme.ai/careers'})), \
             patch('jobagent.pipeline.compose_email', return_value=('Application', 'Draft')):
            db.domain_known.return_value = False
            db.add_lead.return_value = 42
            process_company(self.company, self.results)
            self.assertEqual(db.add_lead.call_args.kwargs['email'], 'hr@acme.ai')


if __name__ == '__main__':
    unittest.main()
