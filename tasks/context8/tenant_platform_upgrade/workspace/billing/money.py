from decimal import Decimal

def cents(value):
    return Decimal(str(value))

def amount(units, rate):
    return units * rate
