from datetime import datetime, timedelta
from core.database import getAllLocals

def verifyDate(date:str, dateFormat:str=None):
    try:
        return datetime.strptime(date, "%d/%m/%Y" if dateFormat==None else dateFormat).date()
    except ValueError:
        return False

def localeIsAvailable(locale:str):
    if locale in getAllLocals():
        return true
    else: return false