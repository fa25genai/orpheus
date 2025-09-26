import logging
import typing
from asyncio import Lock
from typing import Awaitable

from service_status.models.avatar_element_status import AvatarElementStatus
from service_status.models.status import Status
from service_status.models.status_patch import StatusPatch
from service_status.models.step_status import StepStatus

_log = logging.getLogger("status_manager")


class StatusManager:
    status_objects: typing.Dict[str, Status] = {}
    listeners: typing.Dict[str, typing.Dict[str, typing.Callable[[Status], Awaitable[None]]]]

    def __init__(self):
        self.status_objects = {}
        self.listeners = {}
        self.mutex = Lock()

    async def get_status(self, prompt_id: str) -> Status:
        async with self.mutex:
            self._get_status_unsafe(prompt_id)

    async def update_status(self, prompt_id: str, patch: StatusPatch):
        async with self.mutex:
            base = self._get_status_unsafe(prompt_id)

            for (k, v) in patch.__dict__.items():
                if v is not None and k != "steps_avatar_generation":
                    base.__dict__[k] = v

            if base.slide_structure is not None and len(base.steps_avatar_generation) < len(base.slide_structure.pages):
                for i in range(len(base.slide_structure.pages) - len(base.steps_avatar_generation)):
                    base.steps_avatar_generation.append(AvatarElementStatus(
                        audio=StepStatus.NOT_STARTED,
                        video=StepStatus.NOT_STARTED,
                    ))

            if patch.steps_avatar_generation is not None:
                for k, v in patch.steps_avatar_generation.items():
                    try:
                        idx = int(k)
                        base.steps_avatar_generation[idx] = v
                    except Exception as ex:
                        _log.error(
                            "Failed to convert steps avatar generation key '{}' to int: {}".format(
                                k, v
                            ),
                            exc_info=ex,
                        )

            self.status_objects[prompt_id] = base

            if prompt_id in self.listeners:
                for _, listener in self.listeners[prompt_id]:
                    await listener(base)

    async def add_listener(
            self, prompt_id: str, reference: str, listener: typing.Callable[[Status], Awaitable[None]]
    ):
        async with self.mutex:
            if prompt_id not in self.listeners:
                self.listeners[prompt_id] = {}
            self.listeners[prompt_id][reference] = listener
            await listener(await self._get_status_unsafe(prompt_id))

    async def remove_listener(self, prompt_id: str, reference: str):
        async with self.mutex:
            if prompt_id not in self.listeners:
                return
            del self.listeners[prompt_id][reference]
            if len(self.listeners[prompt_id].keys()) == 0:
                self.listeners.pop(prompt_id, None)

    def _get_status_unsafe(self, prompt_id: str) -> Status:
        if prompt_id in self.status_objects:
            return self.status_objects[prompt_id]
        return self._empty_status()

    def _empty_status(self) -> Status:
        return Status(
            stepUnderstanding=StepStatus.NOT_STARTED,
            stepLookup=StepStatus.NOT_STARTED,
            stepLectureScriptGeneration=StepStatus.NOT_STARTED,
            stepSlideStructureGeneration=StepStatus.NOT_STARTED,
            stepSlideGeneration=0,
            stepSlidePostprocessing=StepStatus.NOT_STARTED,
            stepsAvatarGeneration=[],
            lectureSummary=None,
            slideStructure=None,
        )
