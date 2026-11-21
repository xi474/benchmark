import re
import xml.etree.ElementTree as ET


def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {'name', 'result'}:
        return payload['result']
    return payload


def _local(tag):
    if tag.startswith('{'):
        return tag.split('}', 1)[1]
    return tag


def _clean_text(text):
    return text if text is not None else ''


def transform(payloads, contract):
    if len(payloads) != len(contract['inputs']):
        raise ValueError('payload count mismatch')
    raw = _unwrap(payloads[0])
    if not isinstance(raw, dict):
        raise ValueError('input must be object')
    xml_text = raw.get('xml')
    language_codes = raw.get('language_codes')
    if not isinstance(xml_text, str):
        raise ValueError('xml must be string')
    if not isinstance(language_codes, list):
        raise ValueError('language_codes must be list')
    for code in language_codes:
        if not isinstance(code, str) or len(code) != 3 or not code.islower() or not code.isalpha():
            raise ValueError('invalid language code')

    if 'DOCTYPE' in xml_text or 'ENTITY' in xml_text:
        raise ValueError('DOCTYPE/ENTITY forbidden')

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        raise ValueError('bad XML')

    root_tag = _local(root.tag)
    if root_tag not in ('collection', 'record'):
        raise ValueError('bad root')

    records = []
    seen_ids = set()
    record_elems = [root] if root_tag == 'record' else list(root)

    for rec in record_elems:
        if _local(rec.tag) != 'record':
            raise ValueError('unknown element')
        controls = {}
        fields = []
        rec_id = None
        for child in rec:
            ctag = _local(child.tag)
            if ctag == 'controlfield':
                tag = child.get('tag')
                if tag is None or not re.fullmatch(r'\d{3}', tag):
                    raise ValueError('bad controlfield tag')
                if tag in controls:
                    raise ValueError('duplicate controlfield tag')
                controls[tag] = _clean_text(child.text)
                if tag == '001':
                    rec_id = controls[tag]
            elif ctag == 'datafield':
                tag = child.get('tag')
                if tag is None or not re.fullmatch(r'\d{3}', tag):
                    raise ValueError('bad datafield tag')
                subfields = []
                for sf in child:
                    if _local(sf.tag) != 'subfield':
                        raise ValueError('unknown element')
                    code = sf.get('code')
                    if code is None or not re.fullmatch(r'[A-Za-z0-9]', code):
                        raise ValueError('bad subfield code')
                    subfields.append({'code': code, 'value': _clean_text(sf.text)})
                fields.append({'tag': tag, 'subfields': subfields})
            else:
                raise ValueError('unknown element')
        if rec_id is None or rec_id.strip() == '':
            raise ValueError('missing or empty 001')
        if rec_id in seen_ids:
            raise ValueError('duplicate record id')
        seen_ids.add(rec_id)
        records.append({'id': rec_id, 'controls': controls, 'fields': fields})

    records.sort(key=lambda r: r['id'])
    return {'name': contract['name'], 'result': {'records': records}}
