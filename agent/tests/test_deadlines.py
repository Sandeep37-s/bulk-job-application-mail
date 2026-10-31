import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import test_sending
from jobagent import db, deadlines, sending


class DeadlineTests(unittest.TestCase):
    setUp = test_sending.SendingTests.setUp
    tearDown = test_sending.SendingTests.tearDown
    def set_deadline(self, lead, at):
        db.kv_set(f'deadline:{lead}', json.dumps({'at': at.isoformat(), 'quote': 'Deadline: test'}))

    def test_nearest_deadline_first(self):
        now = datetime.now(timezone.utc)
        self.set_deadline(self.lead, now + timedelta(days=5))
        second = db.add_lead(domain='urgent.ai', hiring_role='AI Engineer', status='pending')
        db.kv_set(f'auto_eligible:{second}', '1')
        self.set_deadline(second, now + timedelta(hours=2))
        self.assertEqual(sending.pending_queue()[0]['id'], second)

    def test_expired_never_sent(self):
        self.set_deadline(self.lead, datetime.now(timezone.utc) - timedelta(seconds=1))
        with patch.object(sending, 'send_email') as smtp:
            self.assertIn('Expired', sending.send_one(self.lead))
            smtp.assert_not_called()
        self.assertEqual(db.get_lead(self.lead)['status'], 'expired')

    def test_quota_projection(self):
        now = datetime.now(timezone.utc)
        for i in range(40):
            db.add_lead(domain=f'used{i}.ai', sent_at=now.isoformat(), status='sent')
        slots = deadlines.projected_slots([db.get_lead(self.lead)], 40, 2160, now)
        self.assertEqual(slots[0][1], db.day_start(now) + timedelta(days=1))

    def test_send_window(self):
        window = {'send_hours': '09:30-19:30', 'send_days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']}
        ist = deadlines.IST
        with patch.dict(sending.CFG['sending'], window):
            friday_noon = datetime(2026, 10, 23, 12, 0, tzinfo=ist)
            self.assertTrue(deadlines.in_window(friday_noon))
            self.assertEqual(deadlines.next_window_open(datetime(2026, 10, 23, 7, 0, tzinfo=ist)),
                             datetime(2026, 10, 23, 9, 30, tzinfo=ist))
            # Saturday evening -> Monday morning (Sunday is off)
            self.assertEqual(deadlines.next_window_open(datetime(2026, 10, 24, 20, 0, tzinfo=ist)),
                             datetime(2026, 10, 26, 9, 30, tzinfo=ist))
            slots = deadlines.projected_slots([db.get_lead(self.lead)] * 3, 40, 900,
                                              datetime(2026, 10, 23, 19, 20, tzinfo=ist))
            self.assertEqual([s.astimezone(ist).strftime('%a %H:%M') for _, s in slots],
                             ['Fri 19:20', 'Sat 09:30', 'Sat 09:45'])

    def test_outside_hours_not_sent(self):
        with patch.dict(sending.CFG['sending'], {'send_hours': '00:00-00:01', 'send_days': ['Mon']}),              patch.object(sending, 'in_window', return_value=False), patch.object(sending, 'send_email') as smtp:
            self.assertIn('Outside sending hours', sending.send_one(self.lead))
            smtp.assert_not_called()

    def test_cap_resets_at_ist_midnight(self):
        yesterday = db.day_start() - timedelta(minutes=1)
        for i in range(40):
            db.add_lead(domain=f'old{i}.ai', sent_at=yesterday.isoformat(timespec='seconds'), status='sent')
        with patch.object(sending, 'send_email') as smtp:
            self.assertTrue(sending.send_one(self.lead).startswith('Sent to'))
            smtp.assert_called_once()

    def test_sleep_after_daily_cap(self):
        self.assertIsNone(sending.sleep_state(40))
        for i in range(39):
            db.add_lead(domain=f'used{i}.ai', sent_at=db.now(), status='sent')
        self.assertEqual(sending.sleep_state(40), 'queued')  # 39 sent + 1 queued fills today
        db.kv_set(f'deadline:{self.lead}', json.dumps({'at': None, 'quote': 'Apply by tomorrow'}))
        self.assertEqual(sending.sleep_state(40), 'queued')  # unverified deadline still sends
        db.add_lead(domain='last.ai', sent_at=db.now(), status='sent')
        self.assertEqual(sending.sleep_state(40), 'full')

    def test_only_source_backed_quote(self):
        company = dict(source_url='https://acme.ai/jobs', deadline_text='Apply by 2026-10-25')
        deadlines.save_evidence(self.lead, company, [dict(url='https://other.ai', snippet=company['deadline_text'])])
        self.assertIsNone(deadlines.deadline_for(self.lead))
        deadlines.save_evidence(self.lead, company, [dict(url=company['source_url'], snippet=company['deadline_text'])])
        self.assertEqual(deadlines.deadline_for(self.lead).astimezone(deadlines.IST).day, 25)

    def test_ambiguous_deadline_sent_automatically(self):
        db.kv_set(f'deadline:{self.lead}', json.dumps({'at': None, 'quote': 'Hiring closes once both positions are filled.'}))
        with patch.object(sending, 'send_email') as smtp:
            self.assertTrue(sending.send_one(self.lead).startswith('Sent to'))
            smtp.assert_called_once()

    def test_closed_or_past_dated_post_expires(self):
        for quote in ('No longer accepting applications', 'Date : Monday, 12 Oct 2025  Time : 12:00 PM'):
            db.update_lead(self.lead, status='pending')
            db.kv_set(f'deadline:{self.lead}', json.dumps({'at': None, 'quote': quote}))
            with patch.object(sending, 'send_email') as smtp:
                self.assertIn('Expired', sending.send_one(self.lead))
                smtp.assert_not_called()
        db.kv_set(f'deadline:{self.lead}', json.dumps({'at': None, 'quote': 'Walk-in on 12 Oct 2099'}))
        self.assertFalse(deadlines.expired(self.lead))

    def test_date_formats_and_no_guessing(self):
        self.assertIsNotNone(deadlines.parse_deadline('Deadline: 25 October 2026'))
        self.assertIsNone(deadlines.parse_deadline('Apply by tomorrow'))
        self.assertIsNone(deadlines.parse_deadline('Published 2026-10-25'))
        self.assertIsNone(deadlines.parse_deadline('Deadline 2026-10-25 10:00 PST'))


if __name__ == '__main__':
    unittest.main()
