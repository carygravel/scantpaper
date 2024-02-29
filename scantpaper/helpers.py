"Various helper functions"

import re
from dataclasses import dataclass
import logging
import subprocess
import datetime

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


def collate_metadata(settings, today_and_now):
    "collect metadata from settings dictionary"
    metadata = {}
    for key in ["author", "title", "subject", "keywords"]:
        if key in settings:
            metadata[key] = settings[key]
    metadata["datetime"] = today_and_now + settings["datetime offset"]
    if "use_time" not in settings:
        metadata["datetime"] = metadata["datetime"].replace(hour=0, minute=0, second=0)

    if "use_timezone" not in settings:
        metadata["datetime"] = metadata["datetime"].replace(
            tzinfo=datetime.timezone.utc
        )
    return metadata


def expand_metadata_pattern(**kwargs):
    "expand metadata template"

    # Expand author, title and extension
    for key in ["author", "title", "subject", "keywords", "extension"]:
        if key not in kwargs:
            kwargs[key] = ""
        regex = r"%D" + key[0]
        kwargs["template"] = re.sub(
            regex, kwargs[key], kwargs["template"], flags=re.MULTILINE | re.DOTALL
        )

    # Expand convert %Dx code to %x, convert using strftime and replace
    regex = re.search(
        r"%D([A-Za-z])", kwargs["template"], re.MULTILINE | re.DOTALL | re.VERBOSE
    )
    while regex:
        code = regex.group(1)
        template = f"%{code}"
        result = kwargs["docdate"].strftime(template)
        kwargs["template"] = re.sub(
            rf"%D{code}",
            result,
            kwargs["template"],
            flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
        )
        regex = re.search(
            r"%D([A-Za-z])", kwargs["template"], re.MULTILINE | re.DOTALL | re.VERBOSE
        )

    # Expand basic strftime codes
    kwargs["template"] = kwargs["today_and_now"].strftime(kwargs["template"])

    # avoid leading and trailing whitespace in expanded filename template
    kwargs["template"] = kwargs["template"].strip()
    if "convert_whitespace" in kwargs and kwargs["convert_whitespace"]:
        kwargs["template"] = re.sub(
            r"\s", r"_", kwargs["template"], flags=re.MULTILINE | re.DOTALL
        )
    return kwargs["template"]
