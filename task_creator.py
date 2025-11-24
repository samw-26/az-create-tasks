import argparse
import sys
from msrest.exceptions import ClientException
from azure.devops.v7_1.work_item_tracking import WorkItemTrackingClient, JsonPatchOperation


class TaskCreator:
    def __init__(self, args: argparse.Namespace, client: WorkItemTrackingClient, tasks: list[dict]):
        self.args = args
        self.client = client
        self.tasks = tasks
        self.base_url: str = client.normalized_url
        self.project: str = self.args.project
        self.area: str = self.args.area
        self.iteration: str = self.args.iteration

    def _get_work_item(self, id: int, fields: list[str] | None = None):
        return self.client.get_work_item(id, self.project, fields)

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
                        'url': f'{self.base_url}/{self.args.project}/_apis/wit/workitems/{id}'
                    }
                ))

        work_item = context['client'].create_work_item(
            patch_document,
            project=self.args.project,
            type='task',
            validate_only=self.args.dry_run
        )
        return None if self.args.dry_run else work_item._links.additional_properties['html']['href']

    def _iterate_tasks(self, client: WorkItemTrackingClient, parent: int | None = None):
        for task in self.tasks:
            name = task['name']
            try:
                if parent is not None:
                    parent_item = self._get_work_item(
                        parent, ['System.AreaPath', 'System.IterationPath'])
                    area = parent_item.fields['System.AreaPath']
                    iteration = parent_item.fields['System.IterationPath']
                else:
                    area = self.area
                    iteration = self.iteration

                context = {
                    'client': client,
                    'name': name,
                    'area': area,
                    'iteration': iteration,
                    'assigned': task.get('assigned'),
                    'parent': parent
                }
                link = self._create_task(context)
                if not self.args.silent and link:
                    print(f'Created task {name}: {link}')
            except ClientException as e:
                print(
                    f'\033[31mException occured when creating task {name}: {e}\033[0m')
                print('Stopping execution...')
                sys.exit(1)

    def create_tasks(self, client: WorkItemTrackingClient):
        parents = self.args.parents
        if not len(parents):
            self._iterate_tasks(client)
        else:
            for parent in parents:
                self._iterate_tasks(client, parent)
