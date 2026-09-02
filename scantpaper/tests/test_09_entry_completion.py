"""test EntryCompletion"""

from entry_completion import EntryCompletion


def model_rows(entry):
    """Return the suggestion rows in model (display) order"""
    model = entry.get_completion().get_model()
    rows = []
    model.foreach(lambda m, _path, itr: rows.append(m.get(itr, 0)[0]))
    return rows


def test_1():
    """Test EntryCompletion"""
    suggestions = ["one", "two", "three"]
    entry = EntryCompletion()
    entry.add_to_suggestions(suggestions)
    assert entry.get_suggestions() == suggestions, "get_suggestions"

    #########################

    entry.add_to_suggestions(["four"])
    example = ["one", "two", "three", "four"]
    assert entry.get_suggestions() == example, "updated suggestions"

    #########################

    entry.add_to_suggestions(["two"])
    assert entry.get_suggestions() == example, "ignored duplicates in suggestions"


def test_substring_match():
    """Text occurring in the middle of a suggestion matches"""
    entry = EntryCompletion()
    entry.add_to_suggestions(["La Voz de Galicia", "voxel"])
    entry.set_text("vox")
    rows = model_rows(entry)
    assert "La Voz de Galicia" in rows
    assert "voxel" in rows


def test_case_insensitive_match():
    """Matching is case-insensitive"""
    entry = EntryCompletion()
    entry.add_to_suggestions(["Brian", "Sabrina"])
    entry.set_text("br")
    rows = model_rows(entry)
    assert "Brian" in rows
    assert "Sabrina" in rows


def test_no_match():
    """No suggestion matches when the text appears nowhere"""
    entry = EntryCompletion()
    entry.add_to_suggestions(["Brian", "Sabrina"])
    entry.set_text("xyz")
    completion = entry.get_completion()
    model = entry.get_completion().get_model()
    itr = model.get_iter_first()
    while itr is not None:
        assert entry._match(completion, "xyz", itr, None) is False
        itr = model.iter_next(itr)


def test_prefix_matches_before_substring():
    """Prefix matches are ordered before substring-only matches"""
    entry = EntryCompletion()
    entry.add_to_suggestions(["Brian", "Sabrina", "breeze"])
    entry.set_text("br")
    assert model_rows(entry) == ["Brian", "breeze", "Sabrina"]


def test_exact_match_ranks_first():
    """Exact match ranks first"""
    entry = EntryCompletion()
    entry.add_to_suggestions(["Sabrina", "Brian", "Brianna"])
    entry.set_text("Brian")
    assert model_rows(entry) == ["Brian", "Brianna", "Sabrina"]


def test_inline_completion_uses_top_ranked_match():
    """The first suggestion in the model is a prefix match"""
    entry = EntryCompletion()
    entry.add_to_suggestions(["Sabrina", "Brian"])
    entry.set_text("br")
    rows = model_rows(entry)
    assert rows[0].casefold().startswith("br")


def test_empty_text_keeps_insertion_order():
    """Empty entry text renders suggestions in insertion order"""
    entry = EntryCompletion()
    entry.add_to_suggestions(["one", "two", "three"])
    entry.set_text("")
    assert model_rows(entry) == ["one", "two", "three"]


def test_ranking_applies_on_every_keystroke():
    """The model re-orders as the text changes"""
    entry = EntryCompletion()
    entry.add_to_suggestions(["Sabrina", "Brian"])
    entry.set_text("br")
    assert model_rows(entry) == ["Brian", "Sabrina"]
    entry.set_text("Sa")
    assert model_rows(entry) == ["Sabrina", "Brian"]
