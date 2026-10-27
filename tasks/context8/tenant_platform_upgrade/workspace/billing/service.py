def invoice(events, pricing):
    return {'currency': 'USD', 'lines': events, 'total': 0}
