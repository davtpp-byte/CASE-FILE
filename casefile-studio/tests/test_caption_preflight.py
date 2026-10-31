"""Caption-warning regressions runnable without starting a server or touching media."""
import copy
import unittest

import editorial


def project(scene):
    return {
        'id': '1111111111111111', 'title': 'Synthetic caption metadata QA',
        'script': 'Technical synthetic caption.', 'script_origin': 'user',
        'is_demo': False, 'target_minutes': 1, 'assets': [], 'sources': [],
        'review': {'facts': False, 'rights': False, 'picture': False, 'disclosure': False},
        'captions': True, 'scenes': [{'id': '2222222222222222', 'duration': 2,
            'narration': 'Technical synthetic caption.', 'source_ids': [], **scene}],
    }


def estimated(p):
    return any(i['code'] == 'estimated_captions' for i in editorial.inspect(p, check_files=False)['issues'])


class CaptionPreflightTests(unittest.TestCase):
    def test_imported_srt_is_not_word_count_estimated(self):
        p = project({'timing': 'imported-captions', 'captions_exact': True,
                     'captions': [{'start': 0.1, 'end': 1.9, 'text': 'Technical synthetic caption.'}]})
        self.assertFalse(estimated(p))

    def test_empty_imported_interval_does_not_create_fallback(self):
        self.assertFalse(estimated(project({'timing': 'imported-captions', 'captions_exact': True, 'captions': []})))

    def test_explicit_caption_times_take_priority_over_old_timing_label(self):
        self.assertFalse(estimated(project({'timing': 'estimated', 'captions': [{'start': 0, 'end': 1, 'text': 'Synthetic'}]})))

    def test_transcribed_label_without_caption_times_still_uses_fallback(self):
        self.assertTrue(estimated(project({'timing': 'transcribed', 'captions': []})))

    def test_legacy_word_count_fallback_stays_flagged(self):
        self.assertTrue(estimated(project({'timing': 'estimated', 'captions': []})))

    def test_hidden_captions_do_not_raise_visible_fallback_warning(self):
        p = project({'timing': 'estimated', 'captions': []})
        p['captions'] = False
        self.assertFalse(estimated(p))

    def test_warning_check_does_not_approve_anything_or_change_project(self):
        p = project({'timing': 'imported-captions', 'captions_exact': True, 'captions': []})
        before = copy.deepcopy(p)
        editorial.inspect(p, check_files=False)
        self.assertEqual(p, before)
        self.assertFalse(any(p['review'].values()))


if __name__ == '__main__':
    unittest.main()
