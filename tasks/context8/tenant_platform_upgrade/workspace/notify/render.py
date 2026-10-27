def safe_body(value):
    return value

def delivery_key(message, channel):
    return message.get('id','')
