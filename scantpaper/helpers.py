"Various helper functions"

import datetime
import glob
import logging
import os
import re
import subprocess
import weakref
from dataclasses import dataclass

from dialog import MultipleMessage
from i18n import _

logger = logging.getLogger(__name__)

PROCESS_FAILED = -1
SETTING = {}
_MESSAGE_DIALOG = {"dialog": None}


def _weak_callback(obj, method_name):
    "create a weak callback"
    ref = weakref.ref(obj)

    def callback(*args, **kwargs):
        instance = ref()
        if instance:
            return getattr(instance, method_name)(*args, **kwargs)
        return None

    return callback


@dataclass
class Proc:
    """Class for passing returncode, stdout & stderr."""

    returncode: int
    stdout: str
    stderr: str


def exec_command(cmd, pidfile=None):
    "wrapper for subprocess.Popen()"

    logger.info(" ".join(cmd))
    kwargs = {}
    if pidfile is not None:
        # Put the child in its own session so that cancel() can killpg() it
        # without taking down the process group of the whole application.
        kwargs["start_new_session"] = True
    try:
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            **kwargs,
        ) as proc:
            logger.info("Spawned PID %s", proc.pid)
            if pidfile is not None:
                pidfile.write(str(proc.pid))
                pidfile.flush()
            stdout_data, stderr_data = proc.communicate()
            returncode = proc.returncode
    except FileNotFoundError as err:
        returncode, stdout_data, stderr_data = -1, None, str(err)

    return Proc(returncode, stdout_data, stderr_data)


def exec_command_run(
    cmd,
    pidfile=None,
    *,
    check=False,
    capture_output=False,
    text=True,
    shell=False,
    **kwargs,
):
    """run a command like subprocess.run() but record the spawn pid in the
    pidfile so that cancellation can kill the child process group"""
    kwargs = dict(kwargs)
    if pidfile is not None:
        kwargs["start_new_session"] = True
    if capture_output:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    kwargs["text"] = text
    try:
        with subprocess.Popen(cmd, shell=shell, **kwargs) as proc:
            if pidfile is not None:
                pidfile.write(str(proc.pid))
                pidfile.flush()
            stdout_data, stderr_data = proc.communicate()
            returncode = proc.returncode
    except FileNotFoundError as err:
        if check:
            raise
        return subprocess.CompletedProcess(cmd, PROCESS_FAILED, None, str(err))
    if check and returncode != 0:
        raise subprocess.CalledProcessError(
            returncode, cmd, output=stdout_data, stderr=stderr_data
        )
    return subprocess.CompletedProcess(cmd, returncode, stdout_data, stderr_data)


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
        output = proc.stderr

    elif stream == "both":
        output = proc.stdout + proc.stderr

    else:
        logger.error("Unknown stream: '%s'", (stream,))

    regex2 = re.search(regex, output)
    if regex2:
        return regex2.group(1)
    if proc.returncode == PROCESS_FAILED:
        logger.info(proc.stderr)
        return None

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
        if key not in kwargs or kwargs[key] is None:
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
    if kwargs.get("convert_whitespace"):
        kwargs["template"] = re.sub(
            r"\s", r"_", kwargs["template"], flags=re.MULTILINE | re.DOTALL
        )
    return kwargs["template"]


def show_message_dialog(**options):
    "show message dialog"
    dialog = _MESSAGE_DIALOG["dialog"]
    if not dialog:
        dialog = MultipleMessage(title=_("Messages"), transient_for=options["parent"])
        dialog.set_default_size(
            SETTING["message_window_width"], SETTING["message_window_height"]
        )
        _MESSAGE_DIALOG["dialog"] = dialog

    options["responses"] = SETTING["message"]
    dialog.add_message(options)

    response = None
    if dialog.grid_rows > 1:
        dialog.show_all()
        response = dialog.run()

    if response is not None:
        dialog.store_responses(response, SETTING["message"])
    (
        SETTING["message_window_width"],
        SETTING["message_window_height"],
    ) = dialog.get_size()
    dialog.destroy()


def get_tmp_dir(dirname, pattern):
    "If user selects session dir as tmp dir, return parent dir"
    if dirname is None:
        return None
    while re.search(pattern, dirname):
        dirname = os.path.dirname(dirname)
    return dirname


def slurp(file):
    "slurp file"
    if hasattr(file, "read"):
        file.seek(0)
        content = file.read()
        if isinstance(content, bytes):
            return content.decode("utf-8", "replace")
        return content
    with open(file, "r", encoding="utf-8") as fhd:
        return fhd.read()


def recursive_slurp(files):
    """
    Recursively processes a list of files and directories, logging the contents
    of each file.
    """
    for file in files:
        if os.path.isdir(file):
            recursive_slurp(glob.glob(f"{file}/*"))
        else:
            output = slurp(file)
            if output is not None:
                output = output.rstrip()
                logger.info(output)
