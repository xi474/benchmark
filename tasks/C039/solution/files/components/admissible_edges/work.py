def compute(p):
 n=p['nodes'];return [[n.index(a),n.index(b)] for a,b in p['allowed'] if b!=p['root']]
