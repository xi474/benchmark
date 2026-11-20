import argparse
from solution import build_component

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='public_input.json')
    parser.add_argument('--output', default='outputs/result.json')
    args = parser.parse_args()
    build_component(args.input, args.output)
