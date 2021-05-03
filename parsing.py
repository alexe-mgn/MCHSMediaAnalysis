"""
Classes for parsing HTML pages strings.
"""
from typing import *
import itertools as it

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
        for k, f in [("id", self._parse_id),
                     ("title", self._parse_title),
                     ("date", self._parse_date),
                     ("category", self._parse_category),
                     ("image", self._parse_image)]:
            if (v := f(element)) is not None:
                item[k] = v
        return item

    def _parse_id(self, element: lxml.etree.Element) -> Optional[int]:
        if e := self.item_id_xpath(element):
            return int(e[0].strip('/').split('/')[-1])

    def _parse_title(self, element: lxml.etree.Element) -> Optional[str]:
        if e := self.item_title_xpath(element):
            return str(e[0])

    def _parse_date(self, element: lxml.etree.Element) -> Optional[datetime.datetime]:
        if e := self.item_date_xpath(element):
            time, date = e[0].strip().split(' • ')
            return datetime.datetime(*map(int, date.split('.')[::-1]), *map(int, time.split(':')))

    def _parse_category(self, element: lxml.etree.Element) -> Optional[Dict[str, Optional[str]]]:
        category = {}
        if e := self.item_category_id_xpath(element):
            category["name"] = e[0].split('=')[-1]
        if e := self.item_category_xpath(element):
            category["full_name"] = str(e[0])
        if category:
            return category

    def _parse_image(self, element: lxml.etree.Element) -> Optional[str]:
        if e := self.item_image_xpath(element):
            return str(e[0])


class MCHSNewsParser:
    """
    Class for parsing news page (/news/item/./).
    On initialization parses HTML string. Necessary data can be received from .parse()
    """
    base_xpath = lxml.etree.XPath(".//div[@id='block-1'][1]")
    id_xpath = lxml.etree.XPath("./script[not(@src)][1]/text()")
    title_xpath = lxml.etree.XPath(".//*[@itemprop='headline'][1]/text()")
    date_xpath = lxml.etree.XPath(".//div[contains(@class, 'header__date')][1]/text()")
    text_xpath = lxml.etree.XPath(".//article[1]/*[position() > 1]")
    text_subxpath = lxml.etree.XPath(".//text()")
    category_full_names_xpath = lxml.etree.XPath(".//div[contains(@class, 'header__tags')][1]//a/text()")
    category_names_xpath = lxml.etree.XPath(".//div[contains(@class, 'header__tags')][1]//a/@href")
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
        for k, f in [("id", self._parse_id),
                     ("title", self._parse_title),
                     ("date", self._parse_date),
                     ("text", self._parse_text),
                     ("categories", self._parse_categories),
                     ("tags", self._parse_tags),
                     ("image", self._parse_image)]:
            if (v := f(base)) is not None:
                data[k] = v
        return data

    def _parse_id(self, element: lxml.etree.Element) -> Optional[int]:
        if e := self.id_xpath(element):
            return e[0].split('(')[-1].split(')')[0].strip("'/").split('/')[-1]

    def _parse_title(self, element: lxml.etree.Element) -> Optional[str]:
        if e := self.title_xpath(element):
            return str(e[0])

    def _parse_date(self, element: lxml.etree.Element) -> Optional[datetime.datetime]:
        if e := self.date_xpath(element):
            time, date = e[0].strip().split(' • ')
            time = datetime.time(*map(int, time.split(':')))
            if date.count(' ') <= 1:
                if date.lower() == "сегодня":
                    date = datetime.datetime.now(tz=Timezone(3))
                else:
                    # raise ValueError(f'Could not get date from "{date}"')
                    return None
            else:
                day, month, year = date.split()
                day, month, year = int(day), month_to_int(month), int(year)
                if month is None:
                    # raise ValueError(f'Could not parse month name in "{date}"')
                    return None
                date = datetime.date(year, month, day)
            return datetime.datetime.combine(date, time, tzinfo=Timezone(3))

    def _parse_text(self, element: lxml.etree.Element) -> Optional[str]:
        return '\n'.join(map(''.join, map(self.text_subxpath, self.text_xpath(element))))

    def _parse_categories(self, element: lxml.etree.Element) -> Optional[List[Dict[str, Optional[str]]]]:
        categories = [dict(**name, **full_name)
                      for name, full_name
                      in it.zip_longest(({"name": e.strip('/').split('=')[-1]}
                                         for e in self.category_names_xpath(element)),
                                        ({"full_name": str(e)} for e in self.category_full_names_xpath(element)),
                                        fillvalue={})]
        if categories:
            return categories

    def _parse_tags(self, element: lxml.etree.Element) -> Optional[List[Dict[str, Optional[str]]]]:
        tags = [dict(**tag_id, **name)
                for tag_id, name
                in it.zip_longest(({"id": int(e.strip('/').split('/')[-1])}
                                   for e in self.tag_ids_xpath(element)),
                                  ({"name": str(e)} for e in self.tags_xpath(element)),
                                  fillvalue={})]
        if tags:
            return tags

    def _parse_image(self, element: lxml.etree.Element) -> Optional[str]:
        if e := self.image_xpath(element):
            return str(e[0])
