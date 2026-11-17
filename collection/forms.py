from django import forms

from .models import NOTES_MAX_LENGTH


class NotesForm(forms.Form):
    """A personal note on a collection entry or a wish: plain text, at most 500 characters."""

    notes = forms.CharField(
        label="Note",
        max_length=NOTES_MAX_LENGTH,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text=f"Up to {NOTES_MAX_LENGTH} characters.",
        error_messages={
            # A blank note says nothing; clearing a note is Delete note's job.
            "required": "Write a note, or use Delete note to remove it.",
            "max_length": "Notes can be at most %(limit_value)d characters; "
            "this one has %(show_value)d.",
        },
    )
