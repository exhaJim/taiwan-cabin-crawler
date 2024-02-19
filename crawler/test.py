import unittest
from jml import JmlScraper
import pandas as pd


class TestJmlScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = JmlScraper(year=2024, month=3)

    def test_get_csrf_token(self):
        token = self.scraper._get_csrf_token()
        self.assertIsInstance(token, str)
        self.assertNotEqual(token, '')

    def test_scrape(self):
        self.scraper._scrape()
        self.assertTrue(self.scraper.scraped)
        self.assertIsInstance(self.scraper.result, dict)

    def test_get_data(self):
        data = self.scraper.get_data('2024-03-01', format='list')
        self.assertIsInstance(data, list)

        data = self.scraper.get_data('2024-03', format='pandas')
        self.assertIsInstance(data, pd.DataFrame)


if __name__ == '__main__':
    unittest.main()
