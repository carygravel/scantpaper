"test EntryCompletion"

from entry_completion import EntryCompletion


def test_1():
    "test EntryCompletion"
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
