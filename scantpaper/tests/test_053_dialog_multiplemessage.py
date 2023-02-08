"test MultipleMessage class"
from dialog import MultipleMessage, filter_message, munge_message
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


def test_1():
    "test MultipleMessage class"
    # Translation.set_domain('gscan2pdf')
    window = Gtk.Window()

    dialog = MultipleMessage(title="title", transient_for=window)
    assert isinstance(dialog, MultipleMessage), "Created dialog"

    dialog.add_row(
        {
            "page": 1,
            "process": "scan",
            "message_type": "error",
            "text": "message",
            "store_response": True,
        }
    )
    assert dialog.grid_rows == 2, "1 message"

    dialog.add_row(
        {"page": 2, "process": "scan", "message_type": "warning", "text": "message2"}
    )
    assert dialog.grid_rows == 3, "2 messages"

    dialog.cbn.set_active(True)
    assert dialog.list_messages_to_ignore("ok") == [
        "message"
    ], "list_messages_to_ignore"

    dialog.add_row(
        {
            "page": 1,
            "process": "scan",
            "message_type": "error",
            "text": "my message3\n",
            "store_response": True,
        }
    )
    assert dialog.cbn.get_inconsistent() is True, "inconsistent if states different"
    dialog.cbn.set_active(False)
    dialog.cbn.set_active(True)
    assert dialog.list_messages_to_ignore("ok") == [
        "message",
        "my message3",
    ], "chop trailing whitespace"

    dialog = MultipleMessage(title="title", transient_for=window)
    dialog.add_message(
        {
            "page": 1,
            "process": "scan",
            "message_type": "error",
            "text": "[image2 @ 0x1338180] Encoder did not produce proper pts, making some up.",
        }
    )
    assert dialog.grid_rows == 2, "add_message single message"

    responses = {}
    dialog = MultipleMessage(title="title", transient_for=window)
    dialog.add_message(
        {
            "page": 1,
            "process": "scan",
            "message_type": "error",
            "store_response": True,
            "responses": responses,
            "text": "[image2 @ 0xc596e0] Using AVStream.codec to pass codec parameters "
            """to muxers is deprecated, use AVStream.codecpar instead.
[image2 @ 0x1338180] Encoder did not produce proper pts, making some up.""",
        }
    )
    assert dialog.grid_rows == 3, "add_message added 2 messages"
    dialog.grid.get_child_at(4, 1).set_active(True)
    assert dialog.cbn.get_inconsistent() is True, "inconsistent if states different"

    dialog.grid.get_child_at(4, 2).set_active(True)
    dialog.store_responses("ok", responses)
    assert len(responses.keys()) == 2, "stored 2 responses"

    assert dialog.cbn.get_inconsistent() is False, "consistent as states same"

    dialog = MultipleMessage(title="title", transient_for=window)
    dialog.add_message(
        {
            "page": 1,
            "process": "scan",
            "message_type": "error",
            "store_response": True,
            "responses": responses,
            "text": "[image2 @ 0xc596e0] Using AVStream.codec to pass codec parameters "
            """to muxers is deprecated, use AVStream.codecpar instead.
[image2 @ 0x1338180] Encoder did not produce proper pts, making some up.""",
        }
    )
    assert dialog.grid_rows == 1, "add_message added no messages"

    assert (
        munge_message(
            "(gimp:26514): GLib-GObject-WARNING : g_object_set_valist: object class "
            """'GeglConfig' has no property named 'cache-size'
(gimp:26514): GEGL-gegl-operation.c-WARNING : Cannot change name of operation class """
            '0xE0FD30 from "gimp:point-layer-mode" to "gimp:dissolve-mode"',
        )
        == [
            "(gimp:26514): GLib-GObject-WARNING : g_object_set_valist: object class "
            "'GeglConfig' has no property named 'cache-size'",
            "(gimp:26514): GEGL-gegl-operation.c-WARNING : Cannot change name of "
            'operation class 0xE0FD30 from "gimp:point-layer-mode" to "gimp:dissolve-mode"',
        ]
    ), "split gimp messages"

    assert (
        munge_message(
            "[image2 @ 0xc596e0] Using AVStream.codec to pass codec parameters to "
            """muxers is deprecated, use AVStream.codecpar instead.
[image2 @ 0x1338180] Encoder did not produce proper pts, making some up.""",
        )
        == [
            "[image2 @ 0xc596e0] Using AVStream.codec to pass codec parameters to "
            "muxers is deprecated, use AVStream.codecpar instead.",
            "[image2 @ 0x1338180] Encoder did not produce proper pts, making some up.",
        ]
    ), "split unpaper messages"

    expected = (
        """Exception 400: memory allocation failed

This error is normally due to ImageMagick exceeding its resource limits. These """
        """can be extended by editing its policy file, which on my system is found at """
        "/etc/ImageMagick-6/policy.xml Please see "
        "https://imagemagick.org/script/resources.php for more information"
    )
    assert (
        munge_message("Exception 400: memory allocation failed") == expected
    ), "extend imagemagick Exception 400"

    assert (
        filter_message(
            "[image2 @ 0x1338180] Encoder did not produce proper pts, making some up."
        )
        == "[image2 @ %%x] Encoder did not produce proper pts, making some up."
    ), "Filter out memory address from unpaper warning"

    expected = (
        "[image2 @ %%x] Using AVStream.codec to pass codec parameters to "
        """muxers is deprecated, use AVStream.codecpar instead.
[image2 @ %%x] Encoder did not produce proper pts, making some up."""
    )
    assert (
        filter_message(
            "[image2 @ 0xc596e0] Using AVStream.codec to pass codec parameters "
            """to muxers is deprecated, use AVStream.codecpar instead.
[image2 @ 0x1338180] Encoder did not produce proper pts, making some up."""
        )
        == expected
    ), "Filter out double memory address from unpaper warning"

    assert (
        filter_message("Error processing with tesseract: Detected 440 diacritics")
        == "Error processing with tesseract: Detected %%d diacritics"
    ), "Filter out integer from tesseract warning"

    assert (
        filter_message(
            "Error processing with tesseract: Warning. Invalid resolution 0 dpi. "
            "Using 70 instead."
        )
        == "Error processing with tesseract: Warning. Invalid resolution %%d dpi. "
        "Using %%d instead."
    ), "Filter out 1 and 2 digit integers from tesseract warning"

    assert (
        filter_message(
            "[image2 @ 0x1338180] Encoder did not produce proper pts, making some up. \n "
        )
        == "[image2 @ %%x] Encoder did not produce proper pts, making some up."
    ), "Filter out trailing whitespace"

    assert (
        filter_message(
            "[image2 @ 0x56054e417040] The specified filename "
            "'/tmp/gscan2pdf-ldks/OHSk_wKy5v.pnm' does not contain an image sequence "
            "pattern or a pattern is invalid."
        )
        == "[image2 @ %%x] The specified filename '/tmp/%%t' does not contain an "
        "image sequence pattern or a pattern is invalid."
    ), "Filter out temporary filename from unpaper warning"
