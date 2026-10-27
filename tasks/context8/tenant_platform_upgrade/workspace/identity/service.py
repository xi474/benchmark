from .normalize import norm

def authorize(request, policy):
    # legacy implementation ignores tenant and deny rules
    role = request.get('role', '')
    return {'allowed': role == 'owner', 'role': role, 'reason': 'legacy'}
