"test dialog.save"

from datetime import date, datetime, timedelta
from dialog.save import Save
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


class MockedDateTime(datetime):
    "mock now"

    @classmethod
    def now(cls):  # pylint: disable=arguments-differ
        return datetime(2018, 1, 1, 0, 0, 0)


def test_basic(mocker):
    "basic tests"
    mocker.patch("dialog.save.datetime.datetime", MockedDateTime)
    dialog = Save(
        title="title",
        transient_for=Gtk.Window(),
        meta_datetime=date(2017, 1, 1),
        select_datetime=True,
        meta_title="title",
        meta_title_suggestions=["title-suggestion"],
        meta_author="author",
        meta_author_suggestions=["author-suggestion"],
        meta_subject="subject",
        meta_subject_suggestions=["subject-suggestion"],
        meta_keywords="keywords",
        meta_keywords_suggestions=["keyword-suggestion"],
    )
    assert isinstance(dialog, Save)

    assert dialog.meta_datetime == date(  # pylint: disable=comparison-with-callable
        2017, 1, 1
    ), "date"
    assert dialog.meta_author == "author", "author"
    assert dialog.meta_title == "title", "title"
    assert dialog.meta_subject == "subject", "subject"
    assert dialog.meta_keywords == "keywords", "keywords"

    dialog._meta_author_widget.set_text("author2")
    assert dialog.meta_author == "author2", "author from Entry()"

    config = {
        "author": "old author",
        "title": "old title",
        "subject": "old subject",
        "keywords": "old keywords",
        "datetime offset": timedelta(seconds=0),
        "other key": "other key",
    }
    dialog.update_config_dict(config)
    assert config == {
        "author": "author2",
        "author-suggestions": [
            "author-suggestion",
        ],
        "title": "title",
        "title-suggestions": [
            "title-suggestion",
        ],
        "subject": "subject",
        "subject-suggestions": [
            "subject-suggestion",
        ],
        "keywords": "keywords",
        "keywords-suggestions": [
            "keyword-suggestion",
        ],
        "datetime offset": timedelta(days=-365, hours=0, minutes=0, seconds=0),
        "other key": "other key",
    }, "updated config"

    metadata = {
        "author": "old author",
        "title": "old title",
        "subject": "old subject",
        "keywords": "old keywords",
        "datetime": datetime(2017, 1, 1, 23, 59, 5),
        "other key": "other key",
    }
    dialog.update_from_import_metadata(metadata)
    assert dialog.meta_datetime == datetime(2017, 1, 1, 23, 59, 5), "date"
    assert dialog.meta_author == "old author", "author"
    assert dialog.meta_title == "old title", "title"
    assert dialog.meta_subject == "old subject", "subject"
    assert dialog.meta_keywords == "old keywords", "keywords"


def test_datetime():
    "test datetime"
    dialog = Save(
        transient_for=Gtk.Window(),
        include_time=True,
        meta_datetime=datetime(2017, 1, 1, 23, 59, 5),
        select_datetime=True,
    )
    assert dialog.meta_datetime == datetime(  # pylint: disable=comparison-with-callable
        2017, 1, 1, 23, 59, 5
    ), "date and time"


def test_now(mocker):
    "test not setting datetime"
    now = datetime(2018, 1, 1, 0, 0, 0)
    mocker.patch("dialog.save.datetime.datetime", MockedDateTime)
    dialog = Save(
        transient_for=Gtk.Window(),
        include_time=True,
        meta_datetime=datetime(2017, 1, 1, 23, 59, 5),
    )
    assert (
        dialog.meta_datetime == now  # pylint: disable=comparison-with-callable
    ), "now"
