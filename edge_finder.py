"""
EdgeFinder classes for fast 1d point search.
"""

from typing import *
import abc

import asyncio

import aiohttp

from fetching import MCHSFetcher

__all__ = ["AbstractEdgeFinder", "AbstractSteppingEdgeFinder", "DividingEdgeFinder", "SplittingEdgeFinder"]


class AbstractEdgeFinder(abc.ABC):
    """
    Simple class for finding edge of some "range".
    After initialization data should be provided to instance with .validate,
    supporting information whether index is "left" or "right".
    Instance provides priority indexes to be checked with .get_probe/.get_probes
    On every validation .recalculate is called.
    Process is stopped and edge considered found when property .found == True
    """

    def __init__(self,
                 left: int = 0,
                 right: int = None,
                 accuracy: int = 1):
        """
        :param left: Currently known greatest "left" index.
        :param right: Currently known lowest "right" index.
        :param accuracy: Required distance between left and right for edge to be found.
        """
        self.left = left
        self.right = right
        self.accuracy = accuracy

    @property
    def found(self) -> bool:
        """
        Return whether edge was found or not.
        """
        return self.left is not None and self.right is not None and (self.right - self.left <= self.accuracy)

    @property
    def edge(self) -> Tuple[int, int]:
        """
        Return (left, right)
        aka greatest valid and lowest not valid indexes.
        """
        return self.left, self.right

    @abc.abstractmethod
    def get_probe(self) -> int:
        """
        Return index to be checked next.
        """

    @abc.abstractmethod
    def get_probes(self) -> List[int]:
        """
        Return preferred indexes to be checked,
        preferably in optimal order.
        """

    @abc.abstractmethod
    def recalculate(self):
        pass

    def validate(self, ind: int, left=True):
        """
        Receive checks whether some index "left" or "right"
        and perform necessary calculations for further edge discovery.
        """
        if left:
            if self.left is None or ind > self.left:
                self.left = ind
        else:
            if self.right is None or ind < self.right:
                self.right = ind
        if self.left is not None and self.right is not None and self.left > self.right:
            raise RuntimeError("Left index became greater than right.")
        self.recalculate()

    def check(self, ind: int) -> bool:
        """
        Check function to be used by automatic find.
        :return: index is left
        """
        yield None
        raise NotImplementedError("Check function is not implemented.")

    def find(self):
        """
        Automatically find edge.
        Check method have to be implemented to function.
        """
        while not self.found:
            probe = self.get_probe()
            self.validate(probe, left=self.check(probe))


class AbstractSteppingEdgeFinder(AbstractEdgeFinder):
    """
    Abstract edge finder that probes indexes with certain distance,
    lowering "step" on each edge cross.
    """

    def __init__(self, left: int = 0, right: int = None, step: int = 100, accuracy: int = 1):
        """
        :param step: initial step.
        """
        super().__init__(left, right, accuracy)
        self.step = step
        self.check_left = True

    def get_probe(self) -> int:
        return (self.left + self.step) \
            if self.left is not None and (self.check_left or self.right is None) \
            else (self.right - self.step)

    def get_probes(self) -> List[int]:
        if self.left is not None and self.right is not None:
            center = int((self.left + self.right) // 2)
            left = min(self.left + self.step, self.right - 1)
            right = max(self.right - self.step, self.left + 1)
            return [ee for e in zip(
                range(left, min(max(center + 1, left + 1), self.right), self.step),
                range(right, max(min(center - 1, right - 1), self.left), -self.step)
            ) for ee in (e if e[0] != e[1] else e[:1])]
        else:
            return [self.get_probe()]

    def recalculate(self):
        raise NotImplementedError("Class is partially abstract and doesn't implement recalculation")

    def validate(self, ind: int, left=True):
        super().validate(ind, left)
        self.check_left = not left


class DividingEdgeFinder(AbstractSteppingEdgeFinder):
    """
    Edge finder that divides step value by coef when necessary.
    """

    def __init__(self, left: int = 0, right: int = None, step: int = 100, accuracy: int = 1, coef: float = 2):
        super().__init__(left, right, step, accuracy)
        self.coef = coef
        self.recalculate()

    def recalculate(self):
        if self.left is not None and self.right is not None:
            while self.step > 1 and self.right - self.left <= self.step:
                self.step = max(int(self.step // self.coef), 1)


class SplittingEdgeFinder(AbstractSteppingEdgeFinder):
    """
    Edge finder that have step value equal to fraction of search distance.
    """

    def __init__(self, left: int = 0, right: int = None, step: int = 100, accuracy: int = 1, probes: int = 10):
        super().__init__(left, right, step, accuracy)
        self.probes = probes
        self.recalculate()

    def recalculate(self):
        if self.left is not None and self.right is not None:
            self.step = max(int((self.right - self.left) // self.probes), 1)


class MCHSPageEdgeFinder(MCHSFetcher):
    """
    Class that uses edge finders to find last valid news page.
    """

    # TaskClass = MCHSPageEdgeRequest

    class PageRequestTask(MCHSFetcher.PageRequestTask):
        manager: "MCHSPageEdgeFinder"

        async def response(self, resp: aiohttp.ClientResponse, **kwargs):
            await super().response(resp, **kwargs)
            await self.manager.validate(self.page, valid=resp.ok, resp=resp)

    def __init__(self,
                 loop: asyncio.AbstractEventLoop = None,
                 session: aiohttp.ClientSession = None,
                 edge_finder: AbstractEdgeFinder = None,
                 max_page_requests: int = None, max_news_requests: int = None,
                 max_requests: int = None):
        super().__init__(loop, session, max_page_requests, max_news_requests, max_requests)
        self.edge_finder = edge_finder if edge_finder is not None else DividingEdgeFinder(left=1, step=10000, coef=2)

    def test(self):
        requested = {i.page for i in self._tasks}
        for i in self.edge_finder.get_probes():
            if i not in requested:
                self.request_page(i)

    async def validate(self, page: int, valid: bool = False, resp: aiohttp.ClientResponse = None):
        self.edge_finder.validate(page, valid)
        left, right = self.edge_finder.edge
        for i in self._tasks:
            if isinstance(i, self.PageRequestTask) and not left <= i.page <= right:
                i.cancel()
        if not self.edge_finder.found:
            self.test()
