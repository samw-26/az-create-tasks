import argparse
import re
import yaml


class Parser:
    def __init__(self):
        parser = argparse.ArgumentParser(
            description='Create child tasks of work items.')
        parser.add_argument(
            'template_file',
            metavar='<template file>',
            help='YAML file defining child tasks.',
            type=self.parse_yaml
        )
        parser.add_argument(
            'organization',
            metavar='<organization>',
            help='DevOps organization'
        )
        parser.add_argument(
            'project',
            metavar='<project>',
            help='DevOps project'
        )
        parser.add_argument(
            '--parents',
            metavar='<parent id>',
            help='Ids of the parent work items. Tasks created will use their parent\'s area and iteration paths.',
            nargs='+',
            default=[],
            type=int
        )
        parser.add_argument(
            '--area',
            metavar='<area>',
            help='DevOps area path. Only applicable when no parents are given.'
        )
        parser.add_argument(
            '--iteration',
            metavar='<iteration>',
            help='DevOps iteration path. Only applicable when no parents are given.'
        )
        parser.add_argument(
            '--set',
            action='append',
            metavar='<key>=<value>',
            help='Define custom variables. In the template file, reference them with $KEY. Names cannot start with a digit.',
            type=self.parse_set_vars,
            default=[]
        )
        parser.add_argument(
            '--values',
            metavar='<value>',
            help='Ordered values to be substituted into placeholders $1,$2,... in the template file',
            nargs='+',
            default=[]
        )
        parser.add_argument(
            '--update-pat',
            help='When this flag is present, show prompt to enter new personal access token',
            action='store_true',
        )
        parser.add_argument(
            '--dry-run',
            help='Prints the tasks defined in the yaml file with their variable substitutions. Validates creating work items.',
            action='store_true'
        )
        parser.add_argument(
            '-s', '--silent',
            help='Suppress log messages',
            action='store_true'
        )
        self.args = parser.parse_args()

    def parse_yaml(self, file_name: str):
        VALID_TASK_PROPERTIES = ['name', 'assigned']
        try:
            with open(file_name, 'r') as f:
                result = yaml.safe_load(f)
            if result is None:
                raise argparse.ArgumentTypeError('Invalid yaml file')
            if 'tasks' not in result:
                raise argparse.ArgumentTypeError(
                    '"tasks" key not in yaml file')
            if not isinstance(result['tasks'], list):
                raise argparse.ArgumentTypeError('tasks is not an array')

            task_key_types = {
                'name': str,
                'assigned': str
            }

            for i, task in enumerate(result['tasks']):
                task_number = i + 1
                has_name = False
                for key in task:
                    if key not in VALID_TASK_PROPERTIES:
                        raise argparse.ArgumentTypeError(
                            f'Invalid key in Task {task_number}: {key}')
                    if key == 'name':
                        has_name = True
                    if type(task[key]) != task_key_types[key]:
                        raise argparse.ArgumentTypeError(
                            f'Task {task_number} key "{key}" has an invalid type. '
                            + f'Expected {task_key_types[key]}, but received {type(task[key])}'
                        )

                if not has_name:
                    raise argparse.ArgumentTypeError(
                        f'Task {task_number} does not have name')

        except FileNotFoundError:
            raise argparse.ArgumentTypeError('File not found')
        except yaml.YAMLError as e:
            raise argparse.ArgumentTypeError(e)
        return result

    def parse_set_vars(self, var: str):
        if re.match(r'^\d', var) is not None:
            raise argparse.ArgumentTypeError(
                f'Invalid key name, key cannot start with digit: {var}')
        if '=' not in var:
            raise argparse.ArgumentTypeError(
                f'Invalid format, expected "key=value", but received "{var}"')
        key, value = var.split('=', 1)
        return key, value
