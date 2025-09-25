import logging
import subprocess

_log = logging.getLogger("slidev")


class SlidevHelper:
    def __init__(self, prompt_id: str):
        self.prompt_id = prompt_id

    def build_web_distribution(
        self, work_dir: str, source_path: str, output_dir: str, theme_name: str, base_path: str
    ) -> bool:
        cmd = [
            "slidev",
            "build",
            source_path,
            "--out",
            output_dir,
            "--theme",
            theme_name,
            "--base",
            base_path,
        ]
        _log.debug("Invoking slidev command: %s", " ".join(cmd))
        return subprocess.run(cmd, cwd=work_dir).returncode == 0

    def export_pdf(self, work_dir: str, source_path: str, output_file: str) -> bool:
        cmd = ["slidev", "export", source_path, "--output", output_file]
        _log.debug("Invoking slidev command: %s", " ".join(cmd))
        return subprocess.run(cmd, cwd=work_dir).returncode == 0
