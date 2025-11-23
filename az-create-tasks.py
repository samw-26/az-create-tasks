import yaml
import argparse
import re


class TaskCreator:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.template_file = self.args.template_file
        self.values = self.args.values
        self.set_vars = create_var_dict(self.args.set)
        self._substitute_placeholders()

    def _substitute_placeholders(self):
        for task in self.template_file['tasks']:
            for key, value in task.items():
                task[key] = re.sub(
                    r'\$((?P<index>[0-9]+)|(?P<key>\w+))',
                    self._get_sub_value,
                    value
                )

    def _get_sub_value(self, placeholder: re.Match) -> str:
        placeholder_index = placeholder.group('index')
        key = placeholder.group('key')
        index = (
            None if placeholder_index is None
            else int(placeholder_index) - 1
        )
        values_length = len(self.values)

        if (
            index is not None
            and values_length > 0
            and index < values_length
            and index >= 0
        ):
            return self.values[index]

        if key and key in self.set_vars:
            return self.set_vars[key]

        return placeholder.group()


def main():
    parser = argparse.ArgumentParser(
        description='Create child tasks of work items')
    parser.add_argument(
        'template_file',
        metavar='<template file>',
        help='YAML file defining child tasks.',
        type=parse_yaml
    )
    parser.add_argument(
        '--set',
        action='append',
        metavar='<key>=<value>',
        help='Define custom variables. In the template file, reference them with $KEY. Names cannot start with a digit.',
        type=parse_set_vars,
        default=[]
    )
    parser.add_argument(
        '--values',
        metavar='<value>',
        help='Ordered values to be substituted into placeholders $1,$2,... in the template file',
        nargs='+',
        default=[]
    )
    args = parser.parse_args()
    task_creator = TaskCreator(args)
    print(args.template_file, args.set, args.values)


def parse_yaml(file_name: str):
    VALID_TASK_PROPERTIES = ['name', 'assigned']
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
            task_number = i + 1
            has_name = False
            for key in task:
                if key not in VALID_TASK_PROPERTIES:
                    raise argparse.ArgumentTypeError(
                        f'Invalid key in Task {task_number}: {key}')
                if key == 'name':
                    has_name = True

            if not has_name:
                raise argparse.ArgumentTypeError(
                    f'Task {task_number} does not have name')

    except FileNotFoundError:
        raise argparse.ArgumentTypeError('File not found')
    except yaml.YAMLError as e:
        raise argparse.ArgumentTypeError(e)
    return result


def parse_set_vars(var: str):
    if re.match(r'^\d', var) is not None:
        raise argparse.ArgumentTypeError(
            f'Invalid key name, key cannot start with digit: {var}')
    if '=' not in var:
        raise argparse.ArgumentTypeError(
            f'Invalid format, expected: "KEY=VALUE", received: "{var}"')
    key, value = var.split('=', 1)
    return key, value


def create_var_dict(set_vars):
    vars = {}
    for entry in set_vars:
        vars[entry[0]] = entry[1]
    return vars


if __name__ == '__main__':
    main()
