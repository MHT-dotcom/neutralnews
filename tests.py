import unittest
from app import app

class TestNeutralNewsApp(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app = app.test_client()

    def test_index_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Neutral News")

    def test_search_with_valid_query(self):
        data = {'event': 'election 2025'}
        response = self.app.post('/data', data=data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response.get_data(as_text=True), "Summary")

    def test_search_with_empty_query(self):
        data = {'event': ''}
        response = self.app.post('/data', data=data)
        self.assertContains(response.get_data(as_text=True), "Please enter a news event to search for.")

    # Add more test cases as needed

if __name__ == '__main__':
    unittest.main()