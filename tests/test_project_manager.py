import os
import unittest
from unittest.mock import patch, MagicMock

class TestProjectManager(unittest.IsolatedAsyncioTestCase):
    def test_scan_all_projects_structure(self):
        import project_manager
        projects = project_manager.scan_all_projects()
        self.assertIn("systemd", projects)
        self.assertIn("pm2", projects)
        self.assertIn("docker", projects)
        self.assertIn("processes", projects)

    async def test_kill_process_validation(self):
        import project_manager
        # Killing PID 1 must be rejected
        ok, msg = await project_manager.kill_process_by_pid(1)
        self.assertFalse(ok)
        self.assertTrue("xavfli" in msg.lower() or "ruxsat" in msg.lower())

        # Killing bot's own PID must be rejected
        ok, msg = await project_manager.kill_process_by_pid(os.getpid())
        self.assertFalse(ok)

    async def test_control_project_invalid_action(self):
        import project_manager
        ok, msg = await project_manager.control_project("systemd", "nginx", "invalid_action")
        self.assertFalse(ok)

    async def test_get_project_logs(self):
        import project_manager
        logs = await project_manager.get_project_logs("systemd", "nginx", lines=5)
        self.assertIsInstance(logs, str)

if __name__ == "__main__":
    unittest.main()
