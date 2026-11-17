import json
import os
import unittest
from unittest.mock import patch

class TestBootNotifier(unittest.TestCase):
    def test_get_current_boot_id(self):
        import boot_notifier
        boot_id = boot_notifier.get_current_boot_id()
        self.assertIsInstance(boot_id, str)
        self.assertTrue(len(boot_id) > 0)

    def test_is_new_boot_logic(self):
        import boot_notifier
        test_file = "/tmp/test_system_state_bot.json"
        if os.path.exists(test_file):
            os.remove(test_file)

        with patch("boot_notifier.STATE_FILE", test_file):
            # Initially no state file, so is_new_boot is True
            self.assertTrue(boot_notifier.is_new_boot())
            curr_id = boot_notifier.get_current_boot_id()
            boot_notifier.mark_boot_notified(curr_id)
            # Now it shouldn't be a new boot
            self.assertFalse(boot_notifier.is_new_boot())

        if os.path.exists(test_file):
            os.remove(test_file)

    def test_format_boot_alert(self):
        import boot_notifier
        text = boot_notifier.format_boot_alert()
        self.assertTrue("SERVER" in text and ("YONDI" in text or "ISHGA TUSHDI" in text or "YUKLANDI" in text))
        self.assertIn("Uptime", text)

if __name__ == "__main__":
    unittest.main()
