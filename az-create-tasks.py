import yaml
import argparse
import re
import os
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v7_1.work_item_tracking import WorkItemTrackingClient, JsonPatchOperation


class TaskCreator:
    def __init__(self, args: argparse.Namespace, work_item_tracking_client: WorkItemTrackingClient):
        self.args = args
        self.work_item_tracking_client = work_item_tracking_client
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

    def create_tasks(self):
        patch_document = [
            JsonPatchOperation(
               op='add',
               path='/fields/System.Title',
               value='test'
            ),
        ]
        work_item = self.work_item_tracking_client.create_work_item(
            patch_document,
            project=self.args.project,
            type='Task',
        )
        return work_item


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
        '--area',
        metavar='<area>',
        help='DevOps area path'
    )
    parser.add_argument(
        '--iteration',
        metavar='<iteration>',
        help='DevOps iteration path'
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
    parser.add_argument(
        '--pat',
        metavar='<personal access token>',
        help='Personal access token for Azure DevOps. By default uses the value of DEVOPS_PAT environment variable',
        default=os.environ.get('DEVOPS_PAT')
    )
    args = parser.parse_args()
    if not args.pat:
        print('Personal access token not supplied')
        exit()
    credentials = BasicAuthentication('', args.pat)
    org_url = f'https://dev.azure.com/{args.organization}'
    work_item_tracking_client = WorkItemTrackingClient(org_url, credentials)
    task_creator = TaskCreator(args, work_item_tracking_client)
    work_item = task_creator.create_tasks()
    print(work_item._links.html.href)


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
