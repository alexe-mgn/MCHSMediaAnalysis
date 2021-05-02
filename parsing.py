"""
Classes for parsing HTML pages strings.
"""
from typing import *

import datetime

import lxml.etree
import lxml.html

from date_utils import Timezone, month_to_int

__all__ = ["MCHSPageParser", "MCHSNewsParser"]


class MCHSPageParser:
    """
    Class for parsing pages with news lists (/news/./).
    On initialization parses HTML string. Necessary data can be received from .parse().
    """
    base_xpath = lxml.etree.XPath(".//div[@id='block-1'][1]//div[contains(@class, 'cl-holder')][1]/*")
    item_id_xpath = lxml.etree.XPath(".//div[contains(@class, 'cl-item-title')][1]//a[1]/@href")
    item_title_xpath = lxml.etree.XPath(".//div[contains(@class, 'cl-item-title')][1]//a[1]/text()")
    item_date_xpath = lxml.etree.XPath(".//div[contains(@class, 'cl-item-date')][1]/text()")
    item_category_xpath = lxml.etree.XPath(".//span[contains(@class, 'b-preview-news-tag')][1]//a[1]/text()")
    item_category_id_xpath = lxml.etree.XPath(".//span[contains(@class, 'b-preview-news-tag')][1]//a[1]/@href")
    item_image_xpath = lxml.etree.XPath(".//img[1]/@src")

    def __init__(self, html_page: str, parser: lxml.etree.HTMLParser = None):
        """
        Parse HTML tree using LXML.
        """
        self.tree = lxml.html.fromstring(html_page, parser=parser)

    def parse(self) -> List[Dict[str, Any]]:
        """
        Fill .news with results of _parse_item on each element of base_xpath(tree)
        """
        news = []
        parse_item = self._parse_item
        for item_el in self.base_xpath(self.tree):
            news.append(parse_item(item_el))
        return news

    def _parse_item(self, element: lxml.etree.Element) -> Dict[str, Any]:
        """
        Parse news HTML element and return data dict.
        """
        item = {}
        for k, v in [("id", self._parse_id),
                     ("title", self._parse_title),
                     ("date", self._parse_date),
                     ("category", self._parse_category),
                     ("category_id", self._parse_category_id),
                     ("image", self._parse_image)]:
            item[k] = v(element)
        return item

    def _parse_id(self, element: lxml.etree.Element) -> Optional[int]:
        href = self.item_id_xpath(element)[0]
        if href is not None:
            return int(href.strip('/').split('/')[-1])
        return None

    def _parse_title(self, element: lxml.etree.Element) -> Optional[str]:
        return self.item_title_xpath(element)[0]

    def _parse_date(self, element: lxml.etree.Element) -> Optional[datetime.datetime]:
        date_text = self.item_date_xpath(element)[0]
        time, date = date_text.strip().split(' • ')
        return datetime.datetime(*map(int, date.split('.')[::-1]), *map(int, time.split(':')))

    def _parse_category(self, element: lxml.etree.Element) -> Optional[str]:
        return self.item_category_xpath(element)[0]

    def _parse_category_id(self, element: lxml.etree.Element) -> Optional[str]:
        return self.item_category_id_xpath(element)[0].split('=')[-1]

    def _parse_image(self, element: lxml.etree.Element) -> Optional[str]:
        return self.item_image_xpath(element)[0]


class MCHSNewsParser:
    """
    Class for parsing news page (/news/item/./).
    On initialization parses HTML string. Necessary data can be received from .parse()
    """
    base_xpath = lxml.etree.XPath(".//div[@id='block-1'][1]")
    id_xpath = lxml.etree.XPath("./script[not(@src)][1]/text()")
    title_xpath = lxml.etree.XPath(".//*[@itemprop='headline'][1]/text()")
    date_xpath = lxml.etree.XPath(".//div[contains(@class, 'header__date')][1]/text()")
    text_xpath = lxml.etree.XPath(".//article[1]/*[position() > 1]/text()")
    categories_xpath = lxml.etree.XPath(".//div[contains(@class, 'header__tags')][1]//a/text()")
    category_ids_xpath = lxml.etree.XPath(".//div[contains(@class, 'header__tags')][1]//a/@href")
    tags_xpath = lxml.etree.XPath(".//div[contains(@class, 'article-footer')]//a/text()")
    tag_ids_xpath = lxml.etree.XPath(".//div[contains(@class, 'article-footer')]//a/@href")
    image_xpath = lxml.etree.XPath(".//article[1]//img[1]/@src")

    def __init__(self, html_page: str, parser: lxml.html.HTMLParser = None):
        """
        Parse HTML tree using LXML.
        """
        self.tree = lxml.html.fromstring(html_page, parser=parser)

    def parse(self) -> Dict[str, Any]:
        """
        Parse page using functions on .base_xpath(.tree) and return data dict.
        """
        data = {}
        base = self.base_xpath(self.tree)[0]
        for k, v in [("id", self._parse_id),
                     ("title", self._parse_title),
                     ("date", self._parse_date),
                     ("text", self._parse_text),
                     ("categories", self._parse_categories),
                     ("category_ids", self._parse_category_ids),
                     ("tags", self._parse_tags),
                     ("tag_ids", self._parse_tag_ids),
                     ("image", self._parse_image)]:
            data[k] = v(base)
        return data

    def _parse_id(self, element: lxml.etree.Element) -> Optional[int]:
        return int(self.id_xpath(element)[0].split('(')[-1].split(')')[0].strip("'/").split('/')[-1])

    def _parse_title(self, element: lxml.etree.Element) -> Optional[str]:
        return self.title_xpath(element)[0]

    def _parse_date(self, element: lxml.etree.Element) -> Optional[datetime.datetime]:
        date_text = self.date_xpath(element)[0]
        time, date = date_text.strip().split(' • ')
        time = datetime.time(*map(int, time.split(':')))
        if date.count(' ') <= 1:
            if date.lower() == "сегодня":
                date = datetime.datetime.now(tz=Timezone(3))
            else:
                raise ValueError(f'Could not get date from "{date}"')
        else:
            day, month, year = date.split()
            day, month, year = int(day), month_to_int(month), int(year)
            if month is None:
                raise ValueError(f'Could not parse month name in "{date}"')
            date = datetime.date(year, month, day)
        return datetime.datetime.combine(date, time, tzinfo=Timezone(3))

    def _parse_text(self, element: lxml.etree.Element) -> Optional[str]:
        return '\n'.join(self.text_xpath(element))

    def _parse_categories(self, element: lxml.etree.Element) -> Optional[List[str]]:
        return list(self.categories_xpath(element))

    def _parse_category_ids(self, element: lxml.etree.Element) -> Optional[List[str]]:
        return [e.strip('/').split('=')[-1] for e in self.category_ids_xpath(element)]

    def _parse_tags(self, element: lxml.etree.Element) -> Optional[List[str]]:
        return list(self.tags_xpath(element))

    def _parse_tag_ids(self, element: lxml.etree.Element) -> Optional[List[int]]:
        return [int(e.strip('/').split('/')[-1]) for e in self.tag_ids_xpath(element)]

    def _parse_image(self, element: lxml.etree.Element) -> Optional[str]:
        return self.image_xpath(element)[0]
