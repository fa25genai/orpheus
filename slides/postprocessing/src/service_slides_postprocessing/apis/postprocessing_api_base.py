# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing_extensions import Annotated
from service_slides_postprocessing.models.list_slidesets200_response_inner import (
    ListSlidesets200ResponseInner,
)
from service_slides_postprocessing.models.get_slideset200_response import (
    GetSlideset200Response,
)
from service_slides_postprocessing.models.store_slideset_request import StoreSlidesetRequest
from service_slides_postprocessing.models.upload_accepted_response import UploadAcceptedResponse


class BasePostprocessingApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BasePostprocessingApi.subclasses = BasePostprocessingApi.subclasses + (cls,)

    async def list_slidesets(
        self,
    ) -> List[ListSlidesets200ResponseInner]: ...

    async def get_slideset(
        self,
        promptId: Annotated[
            StrictStr, Field(description="The promptId for the requested slideset")
        ],
    ) -> GetSlideset200Response:
        """Returns a slideset in markdown format"""
        ...

    async def store_slideset(
        self,
        store_slideset_request: StoreSlidesetRequest,
    ) -> UploadAcceptedResponse:
        """Accepts a slideset in markdown format"""
        ...
