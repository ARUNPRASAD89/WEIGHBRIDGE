from PyQt5.QtCore import QDate, QTime, QDateTime, QLocale
import datetime

def to_db_date(val):
    """
    Convert a date value to ISO 'yyyy-MM-dd' string for DB.
    Accepts QDate, QDateTime, datetime.date, str.
    Returns '' if value is None or invalid.
    """
    if val is None or val == "":
        return ""
    if isinstance(val, QDate):
        return val.toString("yyyy-MM-dd")
    if isinstance(val, QDateTime):
        return val.date().toString("yyyy-MM-dd")
    if isinstance(val, datetime.date):
        return val.isoformat()
    if isinstance(val, str):
        qdate = QDate.fromString(val, "yyyy-MM-dd")
        if qdate.isValid():
            return qdate.toString("yyyy-MM-dd")
        qdate = QDate.fromString(val, QLocale.system().dateFormat(QLocale.ShortFormat))
        if qdate.isValid():
            return qdate.toString("yyyy-MM-dd")
        return ""
    return ""

def to_db_time(val):
    """
    Convert a time value to ISO 'HH:mm:ss' string for DB.
    Accepts QTime, QDateTime, datetime.time, str.
    Returns '' if value is None or invalid.
    """
    if val is None or val == "":
        return ""
    if isinstance(val, QTime):
        return val.toString("HH:mm:ss")
    if isinstance(val, QDateTime):
        return val.time().toString("HH:mm:ss")
    if isinstance(val, datetime.time):
        return val.strftime("%H:%M:%S")
    if isinstance(val, str):
        qtime = QTime.fromString(val, "HH:mm:ss")
        if qtime.isValid():
            return qtime.toString("HH:mm:ss")
        qtime = QTime.fromString(val, "HH:mm")
        if qtime.isValid():
            return qtime.toString("HH:mm:ss")
        return ""
    return ""

def to_display_date(val):
    """
    Convert a date value to a localized date string for display.
    Accepts QDate, QDateTime, datetime.date, str.
    Returns '' if value is None or invalid.
    """
    if val is None or val == "":
        return ""
    if isinstance(val, QDate):
        qdate = val
    elif isinstance(val, QDateTime):
        qdate = val.date()
    elif isinstance(val, datetime.date):
        qdate = QDate(val.year, val.month, val.day)
    elif isinstance(val, str):
        qdate = QDate.fromString(val, "yyyy-MM-dd")
        if not qdate.isValid():
            qdate = QDate.fromString(val, QLocale.system().dateFormat(QLocale.ShortFormat))
        if not qdate.isValid():
            return val
    else:
        return str(val)
    return qdate.toString(QLocale.system().dateFormat(QLocale.ShortFormat)) if qdate.isValid() else str(val)

def to_display_time(val):
    """
    Convert a time value to 'HH:mm:ss' string for display.
    Accepts QTime, QDateTime, datetime.time, str.
    Returns '' if value is None or invalid.
    """
    if val is None or val == "":
        return ""
    if isinstance(val, QTime):
        qtime = val
    elif isinstance(val, QDateTime):
        qtime = val.time()
    elif isinstance(val, datetime.time):
        qtime = QTime(val.hour, val.minute, val.second)
    elif isinstance(val, str):
        qtime = QTime.fromString(val, "HH:mm:ss")
        if not qtime.isValid():
            qtime = QTime.fromString(val, "HH:mm")
        if not qtime.isValid():
            return val
    else:
        return str(val)
    return qtime.toString("HH:mm:ss") if qtime.isValid() else str(val)