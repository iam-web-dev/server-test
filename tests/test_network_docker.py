import unittest

class TestNetworkDocker(unittest.IsolatedAsyncioTestCase):
    def test_network_manager_ports(self):
        import network_manager
        ports = network_manager.get_listening_ports()
        self.assertIsInstance(ports, list)
        text = network_manager.format_listening_ports()
        self.assertIsInstance(text, str)
        self.assertTrue("PORT" in text.upper() or "ESHITILAYOTGAN" in text.upper() or "HECH QANDAY" in text.upper())

    def test_docker_installed_check(self):
        import docker_manager
        res = docker_manager.is_docker_installed()
        self.assertIsInstance(res, bool)

    async def test_docker_containers_summary(self):
        import docker_manager
        res = await docker_manager.get_containers_summary()
        self.assertIsInstance(res, list)

if __name__ == "__main__":
    unittest.main()
