import yaml
import argparse
import re
import sys
from pprint import pp
from msrest.authentication import BasicAuthentication
from msrest.exceptions import ClientException
from azure.devops.v7_1.work_item_tracking import WorkItemTrackingClient, JsonPatchOperation
import keyring
from getpass import getpass

class TemplateParser:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.template_file: dict = self.args.template_file
        self.tasks: list[dict] = self.template_file['tasks']
        self.values: list[str] = self.args.values
        self.set_vars: dict = create_var_dict(self.args.set)
        self._substitute_placeholders()
    
    def _substitute_placeholders(self):
        for task in self.tasks:
            for key, value in task.items():
                task[key] = re.sub(
                    r'(?P<escape>\\)?\$((?P<index>[0-9]+)|(?P<key>\w+))',
                    self._get_sub_value,
                    value
                )

    def _get_sub_value(self, placeholder: re.Match) -> str:
        if placeholder.group('escape'):
            return placeholder.group()[1:]
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


class TaskCreator:
    def __init__(self, args: argparse.Namespace, client: WorkItemTrackingClient, tasks: list[dict]):
        self.args = args
        self.client = client
        self.tasks = tasks
        self.base_url = client.normalized_url

    def _get_work_item_url(self):
        return f'https://dev.azure.com/{self.args.organization}'

    def _create_task(self, context):
        patch_document = [
            JsonPatchOperation(
               op='add',
               path='/fields/System.Title',
               value=context['name']
            ),
        ]

        fields = {
            'System.AreaPath': context['area'],
            'System.IterationPath': context['iteration'],
            'System.AssignedTo': context['assigned'],
        }

        relations = {
            'System.LinkTypes.Hierarchy-Reverse': context['parent']
        }

        for field, value in fields.items():
            if value is not None and value != '':
                patch_document.append(JsonPatchOperation(
                    op='add',
                    path=f'/fields/{field}',
                    value=value
                ))

        for key, id in relations.items():
            if id is not None:
                patch_document.append(JsonPatchOperation(
                    op='add',
                    path='/relations/-',
                    value={
                        'rel': key,
                        'url': f'{context["client"].normalized_url}/{self.args.project}/_apis/wit/workitems/{id}'
                    }
                ))

        work_item = context['client'].create_work_item(
            patch_document,
            project=self.args.project,
            type='task',
        )
        return work_item._links.additional_properties['html']['href']

    def create_tasks(self, work_item_tracking_client: WorkItemTrackingClient):
        for parent in self.args.parents:
            for task in self.tasks:
                name = task['name']
                context = {
                    'client': work_item_tracking_client,
                    'name': name,
                    'area': self.args.area,
                    'iteration': self.args.iteration,
                    'assigned': task.get('assigned'),
                    'parent': parent
                }
                try:
                    link = self._create_task(context)
                    if not self.args.silent:
                        print(f'Created task {name}: {link}')
                except ClientException as e:
                    print(f'\033[31mException occured when creating task {name}: {e}\033[0m')


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
        '--parents',
        metavar='<parent id>',
        help='Id of parent work item',
        nargs='+',
        default=[],
        type=int
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
        '--update-pat',
        help='When this flag is present, show prompt to enter new personal access token',
        action='store_true',
    )
    parser.add_argument(
        '--dry-run',
        help='Prints the tasks defined in the yaml file with their variable substitutions',
        action='store_true'
    )
    parser.add_argument(
        '-s', '--silent',
        help='Suppress log messages',
        action='store_true'
    )
    args = parser.parse_args()
    if args.dry_run:
        parser = TemplateParser(args)
        pp(parser.template_file, width=200)
        sys.exit()
    pat = keyring.get_password('devops', 'pat')
    if not pat or args.update_pat:
        try:
            pat = getpass('Enter Azure DevOps Personal Access Token: ')
            keyring.set_password('devops', 'pat', pat)
        except KeyboardInterrupt:
            print()
            sys.exit(1)
    credentials = BasicAuthentication('', pat)
    org_url = f'https://dev.azure.com/{args.organization}'
    work_item_tracking_client = WorkItemTrackingClient(org_url, credentials)
    parser = TemplateParser(args)
    task_creator = TaskCreator(args, work_item_tracking_client, parser.tasks)
    try:
        task_creator.create_tasks(work_item_tracking_client)
    except ClientException as e:
        print(e)

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


def parse_set_vars(var: str):
    if re.match(r'^\d', var) is not None:
        raise argparse.ArgumentTypeError(
            f'Invalid key name, key cannot start with digit: {var}')
    if '=' not in var:
        raise argparse.ArgumentTypeError(
            f'Invalid format, expected "key=value", but received "{var}"')
    key, value = var.split('=', 1)
    return key, value


def create_var_dict(set_vars: list[list]) -> dict:
    vars = {}
    for entry in set_vars:
        vars[entry[0]] = entry[1]
    return vars


if __name__ == '__main__':
    main()
