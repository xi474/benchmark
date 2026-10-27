import json

def serialize_report(records, metadata=None):
    return json.dumps({'records':records}).encode()
