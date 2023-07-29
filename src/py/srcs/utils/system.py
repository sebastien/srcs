import subprocess  # nosec: B404


class CommandError(RuntimeError):
    def __init__(self, command: list[str], status: int, err: bytes):
        super().__init__()
        self.command = command
        self.status = status
        self.err = err

    def __str__(self):
        return f"CommandError: '{' '.join(self.command)}', failed with status {self.status}: {self.err}"


# FIXME: Does not do streaming
def shell(
    command: list[str], cwd: str | None = None, input: bytes | None = None
) -> bytes:
    """Runs a shell command, and returns the stdout as a byte output"""
    # FROM: https://stackoverflow.com/questions/163542/how-do-i-pass-a-string-into-subprocess-popen-using-the-stdin-argument#165662
    res = subprocess.run(  # nosec: B603
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, input=input
    )
    if res.returncode == 0:
        return res.stdout
    else:
        raise CommandError(command, res.returncode, res.stderr)


# EOF
