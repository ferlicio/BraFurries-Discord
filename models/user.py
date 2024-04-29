from datetime import datetime

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
    def __init__(self, name, isVip, memberSince, level=None, locale=None, birthday:datetime=None, vipSince=None, warnings:list[Warnings]=[], xp=0, coins=0, inventory:list[Item]=[]):
        self.name = name
        self.isVip = isVip
        self.vipSince = vipSince
        self.memberSince = memberSince
        self.warnings = warnings
        self.birthday = birthday
        self.locale = locale
        self.level = level
        self.xp = xp
        self.coins = coins
        self.inventory = inventory

    def __str__(self):
        return f'Name: {self.name}'
    