# az-create-tasks
Cli tool to create child tasks on user stories in azure boards.

## Installation
`pip install az-create-tasks`

## Usage
```bash
az-create-tasks [-h] [--parents <parent id> [<parent id> ...]]
                       [--area <area>] [--iteration <iteration>]
                       [--set <key>=<value>] [--values <value> [<value> ...]]
                       [--update-pat] [--dry-run] [-s]
                       <template file> <organization> <project>
```

`az-create-tasks` requires a YAML template file argument. A sample has been provided [here](./sample-template.yaml).

The program expects the template file to have a single `tasks` key which will hold a list of all the tasks you wish to add to a single work item. Each task must follow this schema:

- `name: string` Required, name of the task
- `assigned: string` Email of the person assigned the task

### Variable substitution

You can specify placeholder values in your template file by prefixing a `$`. There are two types of variables, ordered and named. Ordered variables are positive integers starting at 1. Named variables are custom names that can include alphabetical characters, numbers, or underscores. Named variables cannot start with a number.

The `$` can be escaped with backslash `\$` to treat it as a literal `$`.

You can provide values for these variables through the `--values` and `--set` options.

The `--values` option accepts a list of values and will substitute in order into `$1, $2, $3, ...` placeholders.

The `--set` option is used to set define individual key value pairs. For each custom variable name add:  
`--set <name>=<value>`

Example `--set reviewer="person@example.com"`.

### Executing

It is recommended that you run your defined command with the `--dry-run` option first. This option will do two things:

- Print the values for each task with variables substituted. Useful for checking if values are as expected.
- Validate that the tasks with the given field values can be created without creating them. If the task cannot be created, an error will be thrown.

The first run of the program will prompt you to enter your Azure DevOps personal access token. Read [here](https://learn.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate?view=azure-devops&tabs=Windows#create-a-pat) for how to create them. This program requires work item read and write permissions. Copy and paste the token into the terminal when prompted.
If you need to change your access token, run the command with `--update-pat` to prompt for a new token.

Example:
`az-create-tasks sample-template.yaml MyOrg MyProject --values "developer@example.com" "reviewer@example.com" --parents 101 102 103`

This command uses the provided template file and creates the defined tasks as children of work items 101, 102, and 103.
All instances of `$1` in the template were replaced with `developer@example.com` and all instances of `$2` were replaced with `reviewer@example.com`.
