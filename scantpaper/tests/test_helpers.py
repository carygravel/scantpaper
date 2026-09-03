"""test helpers coverage."""

import datetime
import gc
import pathlib
import subprocess
from io import BytesIO
from unittest.mock import MagicMock, patch

import helpers
import pytest
from helpers import (
    PROCESS_FAILED,
    Proc,
    _program_version,
    _weak_callback,
    collate_metadata,
    exec_command,
    exec_command_run,
    expand_metadata_pattern,
    get_tmp_dir,
    program_version,
    recursive_slurp,
    show_message_dialog,
    slurp,
)

_LOCAL_TZ = datetime.datetime.now().astimezone().tzinfo


class MockObj:
    """A mock object for testing weak callbacks."""

    def method(self, *args, **kwargs):
        """A mock method that returns its arguments."""
        return args, kwargs


def test_weak_callback():
    """Test _weak_callback."""
    obj = MockObj()
    cb = _weak_callback(obj, "method")
    assert cb(1, a=2) == ((1,), {"a": 2})
    del obj
    gc.collect()
    assert cb(1, a=2) is None


def test_exec_command_success(mocker):
    """Test exec_command success."""
    mock_popen = mocker.patch("subprocess.Popen")
    proc = mock_popen.return_value.__enter__.return_value
    proc.pid = 1234
    proc.communicate.return_value = ("stdout", "stderr")
    proc.returncode = 0

    pidfile = MagicMock()
    res = exec_command(["ls"], pidfile=pidfile)

    assert res.returncode == 0
    assert res.stdout == "stdout"
    assert res.stderr == "stderr"
    pidfile.write.assert_called_with("1234")


def test_exec_command_filenotfound(mocker):
    """Test exec_command file not found."""
    mocker.patch("subprocess.Popen", side_effect=FileNotFoundError("not found"))
    res = exec_command(["nonexistent"])
    assert res.returncode == -1
    assert res.stdout is None
    assert "not found" in res.stderr


def test_exec_command_run_success(mocker):
    """Test exec_command_run success path."""
    mock_popen = mocker.patch("subprocess.Popen")
    proc = mock_popen.return_value.__enter__.return_value
    proc.pid = 4321
    proc.communicate.return_value = ("out", "err")
    proc.returncode = 0

    pidfile = MagicMock()
    res = exec_command_run(["ls"], pidfile=pidfile, capture_output=True, check=True)

    assert res.returncode == 0
    assert res.stdout == "out"
    assert res.stderr == "err"
    pidfile.write.assert_called_with("4321")
    pidfile.flush.assert_called_once()


def test_exec_command_run_check_failure(mocker):
    """Test exec_command_run raises CalledProcessError when check and nonzero."""
    mock_popen = mocker.patch("subprocess.Popen")
    proc = mock_popen.return_value.__enter__.return_value
    proc.communicate.return_value = ("", "boom")
    proc.returncode = 1

    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        exec_command_run(["false"], capture_output=True, check=True)
    assert exc_info.value.returncode == 1
    assert exc_info.value.stderr == "boom"


def test_exec_command_run_no_check_returns_failed(mocker):
    """Test exec_command_run with check=False returns PROCESS_FAILED on FileNotFoundError."""
    mocker.patch("subprocess.Popen", side_effect=FileNotFoundError("not found"))
    res = exec_command_run(["nonexistent"], check=False)
    assert res.returncode == PROCESS_FAILED
    assert res.stdout is None


def test_exec_command_run_check_propagates_filenotfound(mocker):
    """Test exec_command_run with check=True propagates FileNotFoundError."""
    mocker.patch("subprocess.Popen", side_effect=FileNotFoundError("not found"))
    with pytest.raises(FileNotFoundError):
        exec_command_run(["nonexistent"], check=True)


def test_exec_command_run_sets_new_session(mocker):
    """Test exec_command_run starts a new session when a pidfile is given."""
    mock_popen = mocker.patch("subprocess.Popen")
    proc = mock_popen.return_value.__enter__.return_value
    proc.communicate.return_value = ("", "")
    proc.returncode = 0

    exec_command_run(["ls"], pidfile=MagicMock())
    assert mock_popen.call_args.kwargs["start_new_session"] is True


def test_program_version(mocker):
    """Test program_version."""
    mocker.patch("helpers.exec_command", return_value=Proc(0, "version 1.2.3", ""))
    assert program_version("stdout", r"version ([\d.]+)", ["cmd"]) == "1.2.3"


def test_program_version_helper_branches():
    """Test _program_version branches."""
    # both stream
    proc = Proc(0, "out", "err")
    assert _program_version("both", r"(.*)", proc) == "outerr"

    # stderr stream
    assert _program_version("stderr", r"(.*)", proc) == "err"

    # unknown stream
    # Note: helpers.py:81 sets output=None for unknown stream, then re.search fails.
    with patch("helpers.logger") as mock_logger:
        with pytest.raises(TypeError):
            _program_version("unknown", r".*", proc)
        mock_logger.error.assert_called()

    # PROCESS_FAILED
    proc_fail = Proc(PROCESS_FAILED, "", "some error")
    assert _program_version("stdout", r"regex", proc_fail) is None

    # No match
    assert _program_version("stdout", r"nomatch", proc) is None

    # None stdout/stderr
    proc_none = Proc(0, None, None)
    assert _program_version("stdout", r"(.*)", proc_none) == ""


def test_collate_metadata():
    """Test collate_metadata."""
    settings = {
        "author": "me",
        "title": "work",
        "datetime offset": datetime.timedelta(days=1),
        "use_time": True,
        "use_timezone": True,
    }
    now = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    res = collate_metadata(settings, now)
    assert res["author"] == "me"
    assert res["title"] == "work"
    assert res["datetime"] == now + datetime.timedelta(days=1)

    # Test branches without use_time and use_timezone
    settings.pop("use_time")
    settings.pop("use_timezone")
    res = collate_metadata(settings, now)
    assert res["datetime"].hour == 0
    assert res["datetime"].tzinfo == datetime.timezone.utc

    # Test missing metadata keys
    settings = {"datetime offset": datetime.timedelta(0)}
    res = collate_metadata(settings, now)
    assert "author" not in res


def test_expand_metadata_pattern():
    """Test expand_metadata_pattern."""
    kwargs = {
        "template": "%Da %Dt %Ds %Dk %De",
        "author": "A",
        "title": "T",
        "subject": "S",
        "keywords": "K",
        "extension": "E",
        "docdate": datetime.datetime(2022, 1, 1, tzinfo=_LOCAL_TZ),
        "today_and_now": datetime.datetime(2023, 1, 1, tzinfo=_LOCAL_TZ),
        "convert_whitespace": True,
    }

    res = expand_metadata_pattern(**kwargs)
    assert res == "A_T_S_K_E"

    # Test %Dx conversion
    kwargs["template"] = "%DY"  # docdate year
    res = expand_metadata_pattern(**kwargs)
    assert "2022" in res

    # Test convert_whitespace
    kwargs["template"] = "a b"
    kwargs["convert_whitespace"] = True
    res = expand_metadata_pattern(**kwargs)
    assert res == "a_b"

    # Test missing keys or None values
    kwargs = {
        "template": "%Da %Dt",
        "docdate": datetime.datetime(2022, 1, 1, tzinfo=_LOCAL_TZ),
        "today_and_now": datetime.datetime(2023, 1, 1, tzinfo=_LOCAL_TZ),
    }
    res = expand_metadata_pattern(**kwargs)
    # regex = r"%D" + key[0] -> re.sub(regex, "", template)
    # %Da -> "", %Dt -> "" -> " " -> strip() -> ""
    assert res == ""


def test_show_message_dialog(mocker):
    """Test show_message_dialog."""
    # Mock global variables and MultipleMessage
    mock_multiple_message = mocker.patch("helpers.MultipleMessage")

    helpers._MESSAGE_DIALOG = {"dialog": None}
    helpers.SETTING = {
        "message_window_width": 100,
        "message_window_height": 100,
        "message": {},
    }

    mock_mm = mock_multiple_message.return_value
    mock_mm.grid_rows = 2
    mock_mm.run.return_value = 1
    mock_mm.get_size.return_value = (200, 200)

    show_message_dialog(parent=MagicMock())

    assert helpers.SETTING["message_window_width"] == 200
    mock_mm.destroy.assert_called()

    # Test second call when MESSAGE_DIALOG already exists
    helpers._MESSAGE_DIALOG = {"dialog": mock_mm}
    mock_mm.grid_rows = 2
    show_message_dialog(parent=MagicMock())


def test_get_tmp_dir():
    """Test get_tmp_dir."""
    assert get_tmp_dir(None, "pattern") is None
    assert get_tmp_dir("/a/b/c", "b") == "/a"
    assert get_tmp_dir("/a/b/c", "notfound") == "/a/b/c"


def test_slurp(tmp_path):
    """Test slurp."""
    f = tmp_path / "test.txt"
    f.write_text("content", encoding="utf-8")
    assert slurp(str(f)) == "content"


def test_slurp_file_object(tmp_path):
    """Test slurp reads a file object (e.g. a TemporaryFile pidfile)."""
    f = tmp_path / "pid"
    with pathlib.Path(f).open("w+", encoding="utf-8") as fhd:
        fhd.write("1234")
        fhd.flush()
        assert slurp(fhd) == "1234"


def test_slurp_binary_file_object():
    """Test slurp decodes bytes read from a binary file object."""
    fhd = BytesIO(b"1234")
    assert slurp(fhd) == "1234"


def test_recursive_slurp(tmp_path, mocker):
    """Test recursive_slurp."""
    d = tmp_path / "dir"
    d.mkdir()
    f1 = d / "f1.txt"
    f1.write_text("c1", encoding="utf-8")

    # Test file branch
    mock_logger = mocker.patch("helpers.logger")
    recursive_slurp([str(f1)])
    mock_logger.info.assert_called_with("c1")

    # Test dir branch
    mock_logger.reset_mock()
    recursive_slurp([str(d)])
    mock_logger.info.assert_called_with("c1")

    # Test slurp returning None (simulated via mock because real slurp returns string or raises)
    mocker.patch("helpers.slurp", return_value=None)
    recursive_slurp([str(f1)])
