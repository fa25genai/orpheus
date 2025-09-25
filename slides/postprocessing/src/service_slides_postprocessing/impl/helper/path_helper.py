import datetime
import os
from typing import List

from service_slides_postprocessing.models.list_slidesets200_response_inner import (
    ListSlidesets200ResponseInner,
)


class FilePathHelper:
    def __init__(self):
        self.base_path = os.environ.get("SLIDE_STORAGE_BASE_PATH")
        if self.base_path is None:
            self.base_path = "/etc/orpheus/slides/storage"

    def get_theme_path(self, name: str) -> str | None:
        if name == "default":
            return None
        if name == "tum":
            return "/etc/slidev/themes/theme-tum/package"
        return None

    def list_markdown_slides(self) -> List[ListSlidesets200ResponseInner]:
        base_dir = self._get_markdown_dir()
        if os.path.isdir(base_dir):
            markdown_dirs = os.listdir(base_dir)
            return list(
                map(
                    lambda markdown_dir: ListSlidesets200ResponseInner(
                        promptId=markdown_dir,
                        createdAt=datetime.datetime.fromtimestamp(
                            os.path.getctime(os.path.join(base_dir, markdown_dir))
                        ),
                    ),
                    markdown_dirs,
                )
            )
        return []

    def get_markdown_file(self, prompt_id: str, type: str) -> str:
        return os.path.join(self.get_markdown_directory(prompt_id), f"slides-{type}.md")

    def get_asset_file(self, prompt_id: str, path: str) -> str:
        return os.path.join(self.get_markdown_directory(prompt_id), path)

    def get_markdown_directory(self, prompt_id: str) -> str:
        return os.path.join(self._get_markdown_dir(), prompt_id)

    def get_web_directory(self, prompt_id: str) -> str:
        return os.path.join(self._get_web_dir(), prompt_id)

    def get_export_path(self, prompt_id: str) -> str:
        return os.path.join(self._get_export_dir(), f"{prompt_id}.pdf")

    def _get_markdown_dir(self):
        return os.path.join(self.base_path, "raw")

    def _get_web_dir(self):
        return os.path.join(self.base_path, "web")

    def _get_export_dir(self):
        return os.path.join(self.base_path, "pdf")
