import yaml
import argparse

def main():
    parser = argparse.ArgumentParser(description='Create child tasks of work items')
    parser.add_argument('template_file', help='YAML file defining child tasks.', type=parse_yaml)
    parser.add_argument(
        '--set',
        action='append',
        metavar='KEY=VALUE',
        help='Define custom variables. In the template file, reference them with $KEY',
        type=convert_to_dict
    )
    parser.add_argument(
        'values',
        help='Positional values to be substituted into placeholders $1,$2,... in the template file',
        nargs='*'
    )
    args = parser.parse_args()
    print(args.template_file, args.set, args.values)

def parse_yaml(file_name):
    try:
        with open(file_name, 'r') as f:
            result = yaml.safe_load(f)
        if result is None:
            raise argparse.ArgumentTypeError('Invalid yaml file')
        if 'tasks' not in result:
            raise argparse.ArgumentTypeError('"tasks" key not in yaml file')
        if not isinstance(result['tasks'], list):
            raise argparse.ArgumentTypeError('tasks is not an array')
        for i, task in enumerate(result['tasks']):
            if 'name' not in task:
                raise argparse.ArgumentTypeError(f"Task {i + 1} does not have name")
    except FileNotFoundError:
        raise argparse.ArgumentTypeError('File not found')
    return result

def convert_to_dict(var):
    if '=' not in var:
        raise argparse.ArgumentTypeError(f'Invalid format, expected: "KEY=VALUE", received: "{var}"')
    value_dict = {}
    key, value = var.split('=', 1)
    value_dict[key] = value
    return value_dict

if __name__ == '__main__':
    main()
