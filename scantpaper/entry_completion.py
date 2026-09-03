"""Subclass Gtk.Entry to add completion suggestions"""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402


class EntryCompletion(Gtk.Entry):
    """Subclass Gtk.Entry to add completion suggestions"""

    def __init__(self, text=None, suggestions=None):
        """Initialise Gtk."""
        super().__init__()
        completion = Gtk.EntryCompletion()
        completion.set_inline_completion(True)
        completion.set_text_column(0)
        self.set_completion(completion)
        self._model = Gtk.ListStore(str)
        completion.set_model(self._model)
        completion.set_match_func(self._match, None)
        self._suggestions = []
        self.set_activates_default(True)
        self.connect("changed", self._on_changed)

        if text is not None:
            self.set_text(text)
        if suggestions is not None:
            self.add_to_suggestions(suggestions)

    def _match(self, _completion, key, itr, _data):
        return key.casefold() in self._model.get(itr, 0)[0].casefold()

    def _on_changed(self, _entry):
        self._refresh_model()

    def _ordered_suggestions(self, key):
        folded = key.casefold()
        if not folded:
            return list(self._suggestions)
        exact = []
        prefix = []
        substring = []
        rest = []
        for text in self._suggestions:
            text_folded = text.casefold()
            if text_folded == folded:
                exact.append(text)
            elif text_folded.startswith(folded):
                prefix.append(text)
            elif folded in text_folded:
                substring.append(text)
            else:
                rest.append(text)
        return exact + prefix + substring + rest

    def _refresh_model(self):
        key = self.get_text()
        self._model.clear()
        for text in self._ordered_suggestions(key):
            self._model.append([text])

    def get_suggestions(self):
        """Return suggestions"""
        return list(self._suggestions)

    def add_to_suggestions(self, suggestions):
        """Add to suggestions"""
        for text in suggestions:
            if text not in self._suggestions:
                self._suggestions.append(text)
        self._refresh_model()

    def set_suggestions(self, suggestions):
        """Clear and set suggestions"""
        self._suggestions = []
        self.add_to_suggestions(suggestions)
