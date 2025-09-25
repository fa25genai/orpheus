import os


class UrlHelper:
    def __init__(self):
        self.base_url = os.environ.get("SLIDES_DELIVERY_BASE_URL")
        if self.base_url is None:
            self.base_url = "http://slides-delivery:30608"

        self.reference_path = os.environ.get("SLIDE_STORAGE_BASE_PATH")
        if self.reference_path is None:
            self.reference_path = "/etc/orpheus/slides/storage"

    def get_storage_url(self, path: str) -> str | None:
        check_basepath = os.path.commonprefix([self.reference_path, path]) == self.reference_path
        if check_basepath:
            rel_path = os.path.relpath(path, self.reference_path)
            return f"{self.base_url}/{rel_path}"
        return None
