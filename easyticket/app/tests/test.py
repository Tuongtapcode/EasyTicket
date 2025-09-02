import unittest
from app.index import app

class BasicTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_index(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
    unittest.main()
