from datetime import datetime, timedelta

def verifyDate(date:str, dateFormat:str=None):
    try:
        return datetime.strptime(date, "%d/%m/%Y" if dateFormat==None else dateFormat).date()
    except ValueError:
        return False