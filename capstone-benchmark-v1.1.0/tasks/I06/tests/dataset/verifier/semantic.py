def check_value(task,component,actual,expected,request=None):
    try:
        if actual["minimum_cost"]!=expected["minimum_cost"]:return False
        if actual["ranges"]!=expected["ranges"]:return False
        if set(actual["setting_options"])!=set(expected["setting_options"]):return False
        return all(set(actual["setting_options"][k])==set(v) for k,v in expected["setting_options"].items())
    except (TypeError,KeyError,ValueError):return False


def normalize(ident,value):return value
