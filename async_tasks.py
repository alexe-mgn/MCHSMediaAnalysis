"""
Classes for managing asynchronous tasks,
including RequestManager for concurrent requests.
"""

import warnings
from typing import *

import asyncio

from aiohttp.typedefs import StrOrURL
import aiohttp

__all__ = ["TaskManager", "RequestManager"]


class TaskManager:
    """
    Class for managing asynchronous tasks.
    every instance is closely tied to asyncio.AbstractEventLoop functionality
    so loop should be provided or implicitly created during initialization.
    """

    # AsyncTask = asyncio.Task

    class AsyncTask(asyncio.Task):

        def __init__(self, manager: "TaskManager", coro: Coroutine, *,
                     name: str = None):
            self.manager = manager
            super().__init__(coro, loop=self.manager.loop, name=name)

    _tasks = List[AsyncTask]

    def __init__(self, loop: asyncio.AbstractEventLoop = None):
        self.loop = asyncio.get_event_loop() if loop is None else loop
        # self.loop.set_task_factory(self._task_factory)
        self._tasks = []

    def register_task(self, task: AsyncTask):
        """
        Register task in class manager.
        """
        task.add_done_callback(self._task_finished)
        self._tasks.append(task)

    def create_task(self, coro: Coroutine, /):
        """
        Schedule coroutine as a manager task using TaskManager default task class and register_task.
        """
        t = self.AsyncTask(self, coro=coro)
        self.register_task(t)
        return t

    def _task_finished(self, task: AsyncTask, /):
        """
        Private callback for finishing task.
        Unregisters task from task list, calls all_finished when necessary and public callback task_finished.
        """
        self._tasks.remove(task)
        self.task_finished(task)
        task.remove_done_callback(self._task_finished)
        if not self._tasks:
            self.all_finished()

    async def finish_all(self):
        """
        Await all registered tasks to be completed.
        """
        while self._tasks:
            await asyncio.sleep(0)

    def run_all(self):
        """
        Blocking method to start tasks and wait until everything is completed.
        """
        self.loop.run_until_complete(self.finish_all())

    def task_finished(self, task: AsyncTask, /):
        """
        Callback method, called with itself as the only argument every time a task is finished.
        """

    def all_finished(self):
        """
        Callback method, called every time after all tasks are completed and their callbacks executed.
        Tasks are already considered not being run during call.
        """


class RequestManager(TaskManager):
    """
    Class for making asynchronous url requests.
    """
    # AsyncTask = RequestTask
    _session: aiohttp.ClientSession = None
    close_session: bool = True

    class RequestTask(TaskManager.AsyncTask):
        manager: "RequestManager"

        def __init__(self, manager: "RequestManager", url: StrOrURL, method: str = "get", *,
                     name: Optional[str] = ..., **kwargs) -> None:
            """
            Save parameters and initialize request coroutine.
            :param method: request method name to be used.
            :param session: session to call request with, if not provided, create new.
            :param loop: loop to make request in.
            :param name: task name.
            :param kwargs: pass to session request kwargs.
            """
            self.url = url
            self.method = method
            super().__init__(manager, self._request(**kwargs),
                             name=name if name is not None else f"Request {method}: {url}")

        async def _request(self, **kwargs):
            """
            Make a request using configured session and parameters.
            :param kwargs: pass to session request kwargs.
            """
            async with self.manager.session.request(method=self.method, url=self.url, **kwargs) as resp:
                await self.response(resp)
                await self.manager.response(resp, task=self)

        async def response(self, resp: aiohttp.ClientResponse, **kwargs):
            """
            Callback coroutine called with request response from _request.
            """

    def __init__(self, loop: asyncio.AbstractEventLoop = None, session: aiohttp.ClientSession = None):
        super().__init__(loop)
        self._session = session
        self.loop.create_task(self.init(), name="Init")

    async def init(self):
        """
        Initialization called asynchronously after loop start.
        Sets session.
        """
        if self._session is None:
            self.set_session()

    @property
    def session(self) -> aiohttp.ClientSession:
        """
        Currently used session
        :return:
        """
        return self._session

    def request(self, url: StrOrURL, method: str = "get", **kwargs):
        """
        Create url request task.
        """
        self.register_task(self.RequestTask(self, url, method, **kwargs))

    async def response(self, resp: aiohttp.ClientResponse, task: RequestTask = None, **kwargs):
        """
        Callback executed on every response object after Task's own response coroutine.
        """
        pass

    def new_default_session(self) -> aiohttp.ClientSession:
        """
        Create and return session with default needed configuration.
        """
        connector = aiohttp.TCPConnector()
        return aiohttp.ClientSession(connector=connector, loop=self.loop)

    def set_session(self, session: aiohttp.ClientSession = None):
        """
        Set session to be used for requests.
        If no session provided, create new and set close_session to True.
        Called each time request loop is started without open session.
        Depending on close_session, session will be closed on all_finished.
        """
        if session is not None and session is self._session:
            warnings.warn(f"Setting current {self.__class__.__name__} session to the same one.", RuntimeWarning)
        else:
            if self._session and self.close_session:
                self._close_session()
            if session is None:
                session = self.new_default_session()
                self.close_session = True
        self._session = session

    def _close_session(self):
        if not self._session.closed:
            self.loop.create_task(self._session.close(), name="session.close")

    def all_finished(self):
        if self.close_session:
            self._close_session()

    def __del__(self):
        if self.close_session:
            self._close_session()
