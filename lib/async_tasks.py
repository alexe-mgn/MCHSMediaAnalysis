"""
Classes for managing asynchronous tasks,
including RequestManager for concurrent requests.
"""

from typing import *
import traceback
import sys

import asyncio

__all__ = ["TaskManager"]


class TaskManager:
    """
    Class for managing asynchronous tasks.
    every instance is closely tied to asyncio.AbstractEventLoop functionality
    so loop should be provided or implicitly created during initialization.
    """

    class AsyncTask(asyncio.Task):
        """
        Asynchronous task class, closely tied to TaskManager for portable and universal two-way data API.
        """

        async def _coro_wrapper(self, coro: Coroutine):
            self.manager.task_started(self)
            try:
                await coro
            except BaseException:
                etype, evalue, etraceback = sys.exc_info()
                self.manager.task_failed(self, etype, evalue, etraceback)
            else:
                self.manager.task_successful(self)

        def __init__(self, manager: "TaskManager", coro: Coroutine, *,
                     name: str = None):
            self.manager = manager
            super().__init__(self._coro_wrapper(coro), loop=self.manager.loop, name=name)

    def __init__(self, loop: asyncio.AbstractEventLoop = None):
        self._stopping = False
        if loop is None:
            try:
                self.loop = asyncio.get_event_loop()
                if self.loop.is_closed():
                    raise RuntimeError("Current loop is closed.")
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
        else:
            self.loop = loop
        AsyncTask = self.AsyncTask
        self._tasks: List[AsyncTask] = []
        self._frozen_tasks: List[AsyncTask] = []

    def register_task(self, task: AsyncTask):
        """
        Register task in class manager.
        Should be called on every AsyncTask created, this way tasks are added to manager.
        """
        if not self._stopping:
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

    def stop(self):
        self._stopping = True

    def task_started(self, task: AsyncTask, /):
        """
        Callback method, called every time a task is finished without exceptions.
        """

    def task_failed(self, task: AsyncTask, /,
                    etype: Type[BaseException] = None, evalue: BaseException = None, etraceback=None):
        """
        Callback method, called from inside upper-level except block, wrapping all task coroutines.
        """
        traceback.print_exception(etype, evalue, etraceback)

    def task_successful(self, task: AsyncTask, /):
        """
        Callback method, called every time a task is finished without exceptions.
        """

    def task_finished(self, task: AsyncTask, /):
        """
        Callback method, called every time a task is finished.
        """

    def all_finished(self):
        """
        Callback method, called every time after all tasks are completed and their callbacks executed.
        Tasks are already considered not being run during call.
        """
