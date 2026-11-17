import os
import tempfile
import unittest

class TestFileManager(unittest.IsolatedAsyncioTestCase):
    def test_tail_file(self):
        import file_manager
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            for i in range(100):
                f.write(f"Line {i}\n")
            f_path = f.name
        try:
            ok, content = file_manager.tail_file(f_path, lines=10)
            self.assertTrue(ok)
            self.assertIn("Line 99", content)
            self.assertNotIn("Line 0\n", content)
        finally:
            if os.path.exists(f_path):
                os.remove(f_path)

    def test_prepare_file_nonexistent(self):
        import file_manager
        ok, msg, data, filename = file_manager.prepare_file_for_download("/non/existent/file.txt")
        self.assertFalse(ok)
        self.assertTrue("topilmadi" in msg.lower() or "not found" in msg.lower())

    def test_prepare_file_success(self):
        import file_manager
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("Test content 12345")
            f_path = f.name
        try:
            ok, msg, data, filename = file_manager.prepare_file_for_download(f_path)
            self.assertTrue(ok)
            self.assertEqual(data, b"Test content 12345")
            self.assertEqual(filename, os.path.basename(f_path))
        finally:
            if os.path.exists(f_path):
                os.remove(f_path)

    async def test_clean_system_cache_structure(self):
        import file_manager
        res = await file_manager.clean_system_cache()
        self.assertIsInstance(res, dict)
        self.assertIn("status", res)
        self.assertIn("details", res)

if __name__ == "__main__":
    unittest.main()
