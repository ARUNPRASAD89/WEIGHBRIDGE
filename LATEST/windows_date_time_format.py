import locale
locale.setlocale(locale.LC_TIME, '')
from PyQt5.QtCore import QDate, QTime

def get_windows_date_time_format():
    date_fmt = locale.nl_langinfo(locale.D_FMT)
    time_fmt = "HH:mm:ss"
    return date_fmt, time_fmt

# Usage in your UI or print code
date_fmt, time_fmt = get_windows_date_time_format()
now = QDate.currentDate()
current_time = QTime.currentTime()

ui_date = now.toString(date_fmt)
ui_time = current_time.toString(time_fmt)
# Use ui_date and ui_time for display or printing
