from typing import Union
import requests
import re
from bs4 import BeautifulSoup, ResultSet
import datetime
import dataclasses
import pandas as pd


@dataclasses.dataclass
class JmlScraper:
    # 嘉明湖山屋 https://jmlnt.forest.gov.tw/room/index.php

    year: int
    month: int
    url: str = dataclasses.field(
        default='https://jmlnt.forest.gov.tw/room/index.php', init=False)
    csrf_token: str = dataclasses.field(init=False)
    pattern: str = dataclasses.field(
        default=r"(?P<name>.+?)\s*\n(\n剩餘.*\((?P<beds>\d+)\)\s*)?\n目前報名\s*:\s*(?P<current>.\d+)\s*(.*保留.*(?P<reserved>.\d+).*)?", init=False)
    result: dict = dataclasses.field(init=False)
    scraped: bool = dataclasses.field(default=False, init=False)

    def __post_init__(self):
        self.csrf_token = self._get_csrf_token()

    def _get_csrf_token(self) -> str:
        # _get_csrf_token: get csrf token from the website
        response = requests.get(self.url)
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.find('input', {'name': 'csrf'})['value']

    def _scrape(self):
        # _scrape: scrape the data from the website
        params = {
            'date_set[year]': self.year,
            'date_set[month]': self.month,
            'csrf': self.csrf_token
        }
        try:
            response = requests.get(self.url, params=params)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(e)
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        tags = soup.find_all('a')
        self.result = self._parse_tags(tags)
        self.scraped = True

    def _parse_tags(self, tags: list[ResultSet]) -> dict:
        result = {}
        for tag in tags:
            dt = tag.attrs.get('id')
            if dt and dt.startswith('tds_'):
                tag_result = self._parse_tag(tag)
                real_dt = datetime.datetime(
                    self.year, self.month, int(dt[4:])).strftime('%Y-%m-%d')
                result[real_dt] = tag_result
        return result

    def _parse_tag(self, tag: ResultSet) -> list[dict]:
        tag_result = []
        matches = re.finditer(self.pattern, tag.text, re.MULTILINE)
        for match in matches:
            tag_result.append(match.groupdict())
        return tag_result

    def get_data(
        self,
        date: str,
        format='pandas',
    ) -> Union[dict, pd.DataFrame]:
        # YYYY-MM-DD, accept format: 2024-03-01, 2024/03/01, 2024-3-1, 2024/3/1
        # YYYY-MM, accept format: 2024-03, 2024/03, 2024-3, 2024/3
        # format: 'dict'/'pandas', dict of list, or pandas dataframe

        date = date.replace('/', '-')
        std_date = None
        try:
            std_date = datetime.datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            try:
                datetime.datetime.strptime(date, '%Y-%m')
            except ValueError:
                raise ValueError(
                    'Invalid date format, should be YYYY-MM-DD or YYYY-MM')

        if not self.scraped:
            self._scrape()

        # if std_date is None, return the whole month data,
        # otherwise return the data of the date

        if format == 'pandas':
            if std_date is None:
                return pd.DataFrame.from_dict(self.result, orient='index')
            return pd.DataFrame(self.result.get(std_date.strftime('%Y-%m-%d'), []))

        if std_date is None:
            return self.result
        return self.result.get(std_date.strftime('%Y-%m-%d'), [])


if __name__ == '__main__':
    jml = JmlScraper(2024, 3)
    print(jml.get_data('2024-03', format='pandas'))
