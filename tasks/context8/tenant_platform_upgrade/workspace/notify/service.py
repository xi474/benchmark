def build_delivery(message, preferences):
    return {'channel': 'email', 'body': message.get('body',''), 'idempotency_key': message.get('id','')}
