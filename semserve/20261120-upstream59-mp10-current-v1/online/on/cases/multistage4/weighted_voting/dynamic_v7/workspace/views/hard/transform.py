import math


def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {'name', 'result'}:
        return payload['result']
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract['inputs']):
        raise ValueError('payload count mismatch')
    if contract['operation'] != 'hard_vote':
        raise ValueError('wrong operation')

    fit = _unwrap(payloads[0])
    if not isinstance(fit, dict):
        raise ValueError('fit result must be object')

    classes = fit.get('classes')
    if not isinstance(classes, list) or not classes:
        raise ValueError('classes missing')
    members = fit.get('members')
    if not isinstance(members, list):
        raise ValueError('members missing')

    n_classes = len(classes)
    class_index = {c: i for i, c in enumerate(classes)}

    sample_count = None
    for m in members:
        if not isinstance(m, dict):
            raise ValueError('member must be object')
        preds = m.get('predictions')
        if not isinstance(preds, list):
            raise ValueError('member predictions missing')
        if sample_count is None:
            sample_count = len(preds)
        elif len(preds) != sample_count:
            raise ValueError('sample count mismatch')

    if sample_count is None:
        sample_count = 0

    predictions = []
    scores = []
    for s in range(sample_count):
        tally = [0.0] * n_classes
        for m in members:
            fw = m.get('fit_weight')
            if not isinstance(fw, list):
                raise ValueError('fit_weight must be list')
            if len(fw) != sample_count:
                raise ValueError('fit_weight length mismatch')
            sw = fw[s]
            if isinstance(sw, bool) or not isinstance(sw, (int, float)):
                raise ValueError('bad sample weight')
            if isinstance(sw, float) and not math.isfinite(sw):
                raise ValueError('bad sample weight')
            if sw < 0:
                raise ValueError('bad sample weight')
            pred = m['predictions'][s]
            if pred not in class_index:
                raise ValueError('prediction not in classes')
            tally[class_index[pred]] += sw
        best = max(tally)
        chosen = None
        for i, v in enumerate(tally):
            if v == best:
                chosen = classes[i]
                break
        predictions.append(chosen)
        scores.append(tally)

    return {'name': contract['name'], 'result': {'predictions': predictions, 'scores': scores}}
