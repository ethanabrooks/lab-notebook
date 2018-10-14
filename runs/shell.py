# stdlib
import subprocess

# first party
from runs.logger import Logger


class Bash:
    def __init__(self, logger: Logger):
        self.logger = logger

    def cmd(self, args, fail_ok=False, cwd=None):
        process = subprocess.Popen(
            args,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            cwd=cwd,
            universal_newlines=True)
        stdout, stderr = process.communicate(timeout=1)
        if stderr and not fail_ok:
            self.logger.exit(f"Command `{' '.join(args)}` failed: {stderr}")
        return stdout.strip()

    def last_commit(self):
        try:
            return self.cmd('git rev-parse HEAD'.split())
        except OSError:
            self.logger.exit(
                'Could not detect last commit. Perhaps you have not committed yet?')

    def dirty_repo(self):
        return self.cmd('git status --porcelain'.split()) is not ''
