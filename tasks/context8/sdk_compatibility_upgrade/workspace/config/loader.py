def load_config(defaults, file_data, env, explicit):
    result=dict(defaults); result.update(explicit); return result
