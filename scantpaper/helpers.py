"Various helper functions"

import re
from dataclasses import dataclass
import logging
import subprocess

logger = logging.getLogger(__name__)

PROCESS_FAILED = -1


@dataclass
class Proc:
    """Class for passing returncode, stdout & stderr."""

    returncode: int
    stdout: str
    stderr: str


def exec_command(cmd, pidfile=None):
    "wrapper for subprocess.Popen()"

    logger.info(" ".join(cmd))
    try:
        with subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        ) as proc:
            logger.info("Spawned PID %s", proc.pid)
            if pidfile is not None:
                with open(pidfile, "wt", encoding="utf-8") as fhd:
                    fhd.write(str(proc.pid))
            stdout_data, stderr_data = proc.communicate()
            returncode = proc.returncode
    except FileNotFoundError as err:
        returncode, stdout_data, stderr_data = -1, None, str(err)

    return Proc(returncode, stdout_data, stderr_data)


def program_version(stream, regex, cmd):
    "run command and parse version string from output"
    return _program_version(stream, regex, exec_command(cmd))


def _program_version(stream, regex, proc):
    if proc.stdout is None:
        proc.stdout = ""
    if proc.stderr is None:
        proc.stderr = ""
    output = None
    if stream == "stdout":
        output = proc.stdout

    elif stream == "stderr":
        output = proc.srderr

    elif stream == "both":
        output = proc.stdout + proc.stderr

    else:
        logger.error("Unknown stream: '%s'", (stream,))

    regex2 = re.search(regex, output)
    if regex2:
        return regex2.group(1)
    if proc.returncode == PROCESS_FAILED:
        logger.info(proc.stderr)
        return PROCESS_FAILED

    logger.info("Unable to parse version string from: '%s'", output)
    return None
