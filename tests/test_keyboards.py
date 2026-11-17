import unittest
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

class TestKeyboards(unittest.TestCase):
    def test_admin_main_keyboard_buttons(self):
        import keyboards
        kb = keyboards.admin_main_keyboard
        self.assertIsInstance(kb, ReplyKeyboardMarkup)
        all_texts = [btn.text for row in kb.keyboard for btn in row]
        self.assertIn("🚀 Loyihalar & Saytlar", all_texts)
        self.assertIn("💻 Terminal & Shell", all_texts)
        self.assertIn("🌐 Tarmoq & Portlar", all_texts)
        self.assertIn("📜 Loglar & Tozalash", all_texts)

    def test_projects_keyboard(self):
        import keyboards
        dummy = {
            "systemd": [{"name": "my-api", "id": "my-api.service", "status": "active"}],
            "pm2": [],
            "docker": [],
            "processes": [{"name": "bot (1234)", "id": "1234", "status": "running"}]
        }
        ikb = keyboards.get_projects_inline_keyboard(dummy)
        self.assertIsInstance(ikb, InlineKeyboardMarkup)

    def test_terminal_keyboard(self):
        import keyboards
        ikb = keyboards.get_terminal_inline_keyboard()
        self.assertIsInstance(ikb, InlineKeyboardMarkup)

if __name__ == "__main__":
    unittest.main()
