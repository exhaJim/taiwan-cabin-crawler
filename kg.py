from typing import Union
import requests
import re
from bs4 import BeautifulSoup, ResultSet
import datetime
import dataclasses
import pandas as pd

@dataclasses.dataclass
class KuaiguScraper:
    # 檜谷山莊 https://kgonline.forest.gov.tw/room/index.php

    year: int
    month: int
    url: str = dataclasses.field(
        default='https://kgonline.forest.gov.tw/room/index.php', init=False)
    csrf_token: str = dataclasses.field(init=False)
    pattern: str = dataclasses.field(
        default=r".*(?P<name>檜谷山莊|周圍營地).*\s.*[床位四人帳篷]\((?P<beds>\d+)\).*\s.*目前報名\s:\s(?P<current>\d+).*", init=False)
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
        # find by class name: cendle_table
        tags = soup.find_all('div', {'class': 'cendle_table'})
        self.result = self._parse_tags(tags)
        self.scraped = True

    def _parse_tags(self, tags: list[ResultSet]) -> dict:
        result = {}
        for tag in tags:
            dt = tag.attrs.get('id')
            if dt and dt.startswith('tds_'):
                # window.location='/room/order_terms.php?date=2024-03-29'
                # get onclick attribute and extract the date
                date_matches = re.search(
                    r"date=(\d{4}-\d{2}-\d{2})", tag['onclick'])
                if not date_matches:
                    continue
                date = date_matches.group(1)
                tag_result = self._parse_tag(tag)
                print(date, tag_result)
                result[date] = tag_result
        return result

    def _parse_tag(self, tag: ResultSet) -> list[dict]:
        tag_result = []
        matches = re.finditer(self.pattern, tag.text)
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
    kgl = KuaiguScraper(2024, 3)
    print(kgl.get_data('2024-03-04', format='pandas'))
