import sys
from pprint import pp
from msrest.authentication import BasicAuthentication
from azure.devops.v7_1.work_item_tracking import WorkItemTrackingClient
import keyring
from getpass import getpass
from template_parser import TemplateParser
from task_creator import TaskCreator
from parser import Parser

def main():
    try:
        args = Parser().args
        pat = keyring.get_password('devops', 'pat')
        if not pat or args.update_pat:
                pat = getpass('Enter Azure DevOps Personal Access Token: ')
                keyring.set_password('devops', 'pat', pat)
        credentials = BasicAuthentication('', pat)
        org_url = f'https://dev.azure.com/{args.organization}'
        work_item_tracking_client = WorkItemTrackingClient(org_url, credentials)
        template_parser = TemplateParser(args)
        if args.dry_run:
            pp(template_parser.template_file, width=200)

        task_creator = TaskCreator(args, work_item_tracking_client, template_parser.tasks)
        task_creator.create_tasks(work_item_tracking_client)
    except KeyboardInterrupt:
        print()
        sys.exit(1)

if __name__ == '__main__':
    main()
