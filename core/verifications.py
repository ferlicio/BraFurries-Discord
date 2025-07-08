from datetime import datetime, date


def verifyDate(date_str: str, dateFormat: str | None = None) -> date | bool:
    """Return a ``datetime.date`` if the string matches ``dateFormat`` or ``False``."""

    try:
        return datetime.strptime(
            date_str, "%d/%m/%Y" if dateFormat is None else dateFormat
        ).date()
    except ValueError:
        return False


def validate_birthdate(birthday: date) -> None:
    """Ensure ``birthday`` is a plausible past date.

    Raises
    ------
    ValueError
        If ``birthday`` is in the future or before 1900-01-01.
    TypeError
        If ``birthday`` is not a :class:`datetime.date` instance.
    """

    if not isinstance(birthday, date):
        raise TypeError("Birthday must be a date object")

    if birthday > datetime.now().date():
        raise ValueError("Birth date cannot be in the future")

    if birthday < date(1900, 1, 1):
        raise ValueError("Birth date out of allowed range")
