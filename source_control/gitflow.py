#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2015, José Dinuncio <jose.dinuncio@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: gitflow
short_description: Manages git-flow commands.
description:
     - Adds hooks for executing git-flow commands. Git-flow is a collection of
       Git extensions to provide high-level repository operations for
       Vincent Driessen's branching model
       (http://nvie.com/posts/a-successful-git-branching-model/).
       You can install gitflow using your favorite package manager, or from its
       github repository (https://github.com/nvie/gitflow). You can also read
       "Getting Starting -- Gitflow"
       (http://yakiloo.com/getting-started-git-flow/).
version_added: "1.9"
options:
  path:
    description:
      - The path to the git repository. All commands, except 'version' require
        a 'path' option.
    required: false
  command:
    description:
      - git-flow command.
    choices: ['init', 'feature', 'release', 'hotfix', 'version']
    required: true
  action:
    description:
      - Action to execute. All commands, with the exception of 'init' and
        'version' require an 'action' option.
    required: false
    choices: ['start', 'finish', 'list',
              'publish', 'track',
              'rebase', 'checkout', 'pull']
  name:
    description:
      - The name of the git-flow branch where the action will be executed.
        All actions, with the exception of 'list', require a 'name' option.
        For the commands 'release' and 'hotfix' this name uses to be a
        version number.
    required: false
  executable:
    description:
      - Path to the git executable to use. If not supplied, the normal
        mechanism for resolving binary paths will be used.
    required: false
    default: "git"
  remote:
    description:
      - Name of the remote branch to pull. This option is only used with the
        command 'feature', action 'pull'.
    required: false
    default: (empty sting)
  base:
    description:
      - Name of the branch to use as a base for the new git-flow branch.
        This option is only used with the command 'hotfix', action 'start'.
    required: false
    default: (empty string)

author: José Dinuncio
'''

EXAMPLES = '''
# Initializes a git repository to be used for github.
- gitflow: path={{ path }} command=init

# Start a feature branch named 'foo'
- gitflow: path={{ path }} command=feature action=start name=foo

# Finish a feature branch named 'foo'
- gitflow: path={{ path }} command=feature action=finish name=foo

# Start a release branch named '1.5'
- gitflow: path={{ path }} command=release action=start name=1.5

# Finish a release branch named '1.5'
- gitflow: path={{ path }} command=release action=finish name=1.5

# Get git-flow version
- gitflow: command=version

'''

GIT_EXECUTABLE = 'git'


def _gitflow_version(module, git):
    """gitflow version command.

    Always returns changed=False."""
    cmd = '{0} flow version'.format(git)
    rc, out, err = module.run_command(cmd)

    if rc != 0:
        module.fail_json(msg=err, command=cmd)

    module.exit_json(changed=False, command=cmd, version=out.strip())


def _gitflow_init(module, git, path):
    """git-flow init command.

    Returns changed=False if the repository was previously initialized."""
    cmd = '{0} flow init -d'.format(git)
    rc, out, err = module.run_command(cmd, cwd=path)

    if rc != 0:
        module.fail_json(msg=err, command=cmd)

    if 'Already initialized' in err:
        module.exit_json(changed=False, msg=err, command=cmd)
    else:
        module.exit_json(changed=True, msg=err, command=cmd)


def _gitflow_branch(module, git, command, path, action, name, base, remote):
    """git-flow branch commands (feature, release, hotfix)."""
    cmd = _get_cmd(git, command, action, name, base, remote)
    branches = _list(module, git, command, path)
    _exit_if_unchanged(module, cmd, branches, action, name)

    if action == 'list':
        module.exit_json(changed=False, branches=branches)

    rc, out, err = module.run_command(cmd, cwd=path)

    if rc != 0:
        module.fail_json(msg=err, command=cmd)

    module.exit_json(changed=True, msg=err, command=cmd)


def _list(module, git, command, path):
    """Returns a dict with info about git-flow branches of 'command' type."""
    cmd = '{0} flow {1} list'.format(git, command)
    rc, out, err = module.run_command(cmd, cwd=path)

    if rc != 0:
        module.fail_json(msg=err, command=cmd)

    lst = out.splitlines()
    current = [x for x in lst if x.startswith('* ')]
    lst = [x.replace('* ', '').strip() for x in lst]
    current = [x.replace('* ', '').strip() for x in current]
    return dict(list=lst, current=current)


def _get_cmd(git, command, action, name, base, remote):
    """Returns a string representing the command to execute."""
    # git flow {command} {action} {name}
    cmd = '{0} flow {1} {2} {3}'
    if (cmd, action) == ('hotfix', 'start'):
        # git flow hotfix start {name} {base}
        cmd = '{0} flow {1} {2} {3}'
    elif action == 'pull':
        # git flow feature pull {remote} {name}
        cmd = '{0} flow {1} {4} {2}'

    cmd = cmd.format(git, command, action, name, base, remote)
    return cmd


def _exit_if_unchanged(module, cmd, branches, action, name):
    """Exists if it's unnecesary to execute the command."""
    if ((action == 'start' and name in branches['list']) or
            (action == 'finish' and name not in branches['list']) or
            (action == 'checkout') and name in branches['current']):
        module.exit_json(changed=False, command=cmd)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(required=False),
            command=dict(required=True,
                         choices=['init', 'feature', 'release',
                                  'hotfix', 'version']),
            action=dict(required=False,
                        choices=['start', 'finish', 'publish', 'list',
                                 'rebase', 'checkout', 'pull']),
            name=dict(required=False),
            executable=dict(required=False, default=GIT_EXECUTABLE),
            remote=dict(required=False, default=''),
            base=dict(required=False, default=''),
        )
    )

    path = module.params['path']
    git = module.params['executable']
    command = module.params['command']
    action = module.params['action']
    name = module.params['name']
    remote = module.params['remote']
    base = module.params['base']

    if command == 'version':
        _gitflow_version(module, git)

    elif command == 'init':
        _gitflow_init(module, git, path)

    # Added 'support' for completitude, but it won't be used since it's
    # not declared in module's command choices.
    elif command in ['feature', 'release', 'hotfix', 'support']:
        _gitflow_branch(module, git, command, path, action, name,
                        base, remote)


# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.urls import *

main()
