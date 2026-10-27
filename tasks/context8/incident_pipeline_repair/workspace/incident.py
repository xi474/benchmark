def combine(metric, trace, log):
    return {'metric':metric,'trace':trace,'log':log,'has_error':bool(trace['error_services'] or log['counts'].get('error',0))}
