"Subclass Gtk.Entry to add completion suggestions"
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


class EntryCompletion(Gtk.Entry):
    "Subclass Gtk.Entry to add completion suggestions"

    def __init__(self, text=None, suggestions=None):
        super().__init__()
        completion = Gtk.EntryCompletion()
        completion.set_inline_completion(True)
        completion.set_text_column(0)
        self.set_completion(completion)
        model = Gtk.ListStore(str)
        completion.set_model(model)
        self.set_activates_default(True)

        if text is not None:
            self.set_text(text)
        if suggestions is not None:
            self.add_to_suggestions(suggestions)

    def get_suggestions(self):
        "return suggestions"
        completion = self.get_completion()
        suggestions = []
        completion.get_model().foreach(
            lambda model, _path, itr: suggestions.append(model.get(itr, 0)[0])
        )
        return suggestions

    def add_to_suggestions(self, suggestions):
        "add to suggestions"
        completion = self.get_completion()
        model = completion.get_model()
        for text in suggestions:
            flag = False

            def is_duplicate(model, _path, itr, txt):
                nonlocal flag
                if model.get(itr, 0)[0] == txt:
                    flag = True
                return flag  # False=continue

            model.foreach(is_duplicate, text)
            if not flag:
                model.append([text])
