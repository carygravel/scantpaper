"Various helper functions"

import re
import os
from dataclasses import dataclass
import logging
import subprocess
import datetime
from dialog import MultipleMessage
from i18n import _

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
        return PROCESS_FAILED

    logger.info("Unable to parse version string from: '%s'", output)
    return None


def collate_metadata(settings, today_and_now):
    "collect metadata from settings dictionary"
    metadata = {}
    for key in ["author", "title", "subject", "keywords"]:
        if key in settings:
            metadata[key] = settings[key]
    offset = datetime.timedelta(
        days=settings["datetime offset"][0],
        hours=settings["datetime offset"][1],
        minutes=settings["datetime offset"][2],
        seconds=settings["datetime offset"][3],
    )
    metadata["datetime"] = today_and_now + offset
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
    if "convert_whitespace" in kwargs and kwargs["convert_whitespace"]:
        kwargs["template"] = re.sub(
            r"\s", r"_", kwargs["template"], flags=re.MULTILINE | re.DOTALL
        )
    return kwargs["template"]


def show_message_dialog(**options):
    "show message dialog"
    global message_dialog, SETTING
    if not message_dialog:
        message_dialog = MultipleMessage(
            title=_("Messages"), transient_for=options["parent"]
        )
        message_dialog.set_default_size(
            SETTING["message_window_width"], SETTING["message_window_height"]
        )

    options["responses"] = SETTING["message"]
    message_dialog.add_message(options)

    if message_dialog.grid_rows > 1:
        message_dialog.show_all()
        response = message_dialog.run()

    if message_dialog:  # could be undefined for multiple calls
        message_dialog.store_responses(response, SETTING["message"])
        (
            SETTING["message_window_width"],
            SETTING["message_window_height"],
        ) = message_dialog.get_size()
        message_dialog.destroy()


def parse_truetype_fonts(fclist):
    "Build a look-up table of all true-type fonts installed"
    fonts = {"by_file": {}, "by_family": {}}
    regex_tailing_nl = re.compile(r"\n$")
    regex_leading_space = re.compile(r"^\s+")
    regex_tailing_comma = re.compile(r",.*$")
    regex_leading_style = re.compile(r"^style=")
    for font in fclist.split("\n"):
        if re.search(r"ttf:[ ]", font):
            file_family_style = font.split(":")
            if len(file_family_style) == 3:
                file, family, style = file_family_style
                family = regex_leading_space.sub("", family)
                family = regex_tailing_comma.sub("", family)
                style = regex_tailing_nl.sub("", style)
                style = regex_leading_style.sub("", style)
                style = regex_tailing_comma.sub("", style)
                fonts["by_file"][file] = (family, style)
                if family not in fonts["by_family"]:
                    fonts["by_family"][family] = {}
                fonts["by_family"][family][style] = file
    return fonts


def get_tmp_dir(dirname, pattern):
    "If user selects session dir as tmp dir, return parent dir"
    if dirname is None:
        return None
    while re.search(pattern, dirname):
        dirname = os.path.dirname(dirname)
    return dirname
