import argparse
import re


class TemplateParser:
  def __init__(self, args: argparse.Namespace):
      self.args = args
      self.template_file: dict = self.args.template_file
      self.tasks: list[dict] = self.template_file['tasks']
      self.values: list[str] = self.args.values
      self.set_vars: dict = self.create_var_dict(self.args.set)
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

  def create_var_dict(self, set_vars: list[list]) -> dict:
    vars = {}
    for entry in set_vars:
        vars[entry[0]] = entry[1]
    return vars
