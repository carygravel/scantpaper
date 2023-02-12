"test ComboBoxText widget"
from comboboxtext import ComboBoxText


def test_1():
    "test ComboBoxText widget"
    cbt = ComboBoxText()
    assert isinstance(cbt, ComboBoxText), "Created ComboBoxText widget"

    data = [[1, "text 1"], [2, "text 2"]]
    cbt = ComboBoxText(data=data)
    assert cbt.get_num_rows() == 2, "get_num_rows"

    cbt.set_active_index(2)
    assert cbt.get_active_index() == 2, "get_active_index"
    cbt.set_active_index(None)
    assert cbt.get_active_index() == 2, "set_active_index, None"
    cbt.set_active_index(3)
    assert cbt.get_active_index() == 2, "set_active_index, nonexistent"

    cbt.set_active_by_text("text 3")
    assert cbt.get_active_index() == 2, "set_active_by_text, nonexistent"

    cbt.set_active_by_text("text 1")
    assert cbt.get_active_index() == 1, "set_active_by_text"

    assert cbt.get_row_by_text("text 2") == 1, "get_row_by_text"
    assert cbt.get_row_by_text(None) == -1, "get_row_by_text, None"

    cbt.remove_item_by_text("text 3")
    assert cbt.get_num_rows() == 2, "remove_item_by_text, nonexistent"

    cbt.remove_item_by_text(None)
    assert cbt.get_num_rows() == 2, "remove_item_by_text, None"

    cbt.remove_item_by_text("text 1")
    assert cbt.get_num_rows() == 1, "get_num_rows"

    cbt.remove_item_by_text("text 2")
    assert cbt.get_num_rows() == 0, "get_num_rows, to empty model"
