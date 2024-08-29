from datetime import datetime
from models.event import Event

class Warnings():
    def __init__(self, reason, date):
        self.reason = reason
        self.date = date

    def __str__(self):
        return f'Reason: {self.reason}'

    def __repr__(self):
        return f'Reason: {self.reason}'
    

class Item():
    def __init__(self, item, description, amount):
        self.item = item
        self.description = description
        self.amount = amount

    def __str__(self):
        return f'Item: {self.item}'

    def __repr__(self):
        return f'Item: {self.item}'



class User():
    def __init__(self, name, memberSince:datetime, approved = None, approvedAt:datetime = None, id:int = None, username:str = None,isVip:bool=False, isPartner:bool=False, level:int=0, locale=None, birthday:datetime=None, birthdayVerified:bool=False, vipType=None, vipSince=None, warnings:list[Warnings]=[], xp=0, coins=0, inventory:list[Item]=[], staffOf:list[Event]=[]):
        self.name = name
        self.isVip = isVip
        self.isPartner = isPartner
        self.vipType = vipType
        self.vipSince = vipSince
        self.memberSince = memberSince
        self.approved = approved
        self.approvedAt = approvedAt
        self.warnings = warnings
        self.birthday = birthday
        self.birthdayVerified = birthdayVerified
        self.locale = locale
        self.level = level if level else 0
        self.xp = xp if xp else 0
        self.coins = coins if coins else 0
        self.inventory = inventory if inventory else []
        self.staffOf = staffOf
        self.username = username
        self.id = id

    def __str__(self):
        return f'Name: {self.name}'
    
    
class CustomRole():
    def __init__(self, userId, color, iconId):
        self.userId = userId
        self.color = color
        self.iconId = iconId
        pass