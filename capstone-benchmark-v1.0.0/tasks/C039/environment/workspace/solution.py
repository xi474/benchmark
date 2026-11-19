def transform(payload):
    raise NotImplementedError('Implement the public business contract')

def load_payload(path):
    raise NotImplementedError('Load the supplied input path')

def build_component(input_path, output_path):
    raise NotImplementedError('Create the complete artifact at the supplied output path')
