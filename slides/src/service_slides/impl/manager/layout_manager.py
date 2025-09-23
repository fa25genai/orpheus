from typing import List


class LayoutDescription:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description


class LayoutManager:
    async def get_available_layouts(self, courseId: str) -> List[LayoutDescription]:
        pass

    async def get_layout_template(self, courseId: str, layoutName: str):
        pass
