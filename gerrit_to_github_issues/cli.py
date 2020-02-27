# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import logging
import os
import sys

from gerrit_to_github_issues import errors
from gerrit_to_github_issues.engine import update

LOG_FORMAT = '%(asctime)s %(levelname)-8s %(name)s:' \
             '%(funcName)s [%(lineno)3d] %(message)s'  # noqa

LOG = logging.getLogger(__name__)


def validate(namespace: argparse.Namespace):
    arg_dict = vars(namespace)
    if not ((arg_dict['github_user'] and arg_dict['github_password']) or arg_dict['github_token']):
        raise errors.GithubConfigurationError
    return arg_dict


def main():
    parser = argparse.ArgumentParser(
        prog='gerrit-to-github-issues',
        usage='synchronizes GitHub Issues with new changes found in Gerrit',
        description='This script evaluates the following logic on open changes from Gerrit:\n'
                    '1. Check for and extract an issue tag (i.e. "[#3]") from the open change\'s commit message.\n'
                    '2. Check associated Github Issue for a link to the change. If no such link exists, comment it.\n'
                    '3. If the associated issue was closed, re-open it and comment on it describing why it was '
                    're-opened and a link to the Gerrit change that was found.\n'
                    '4. If the Gerrit change\'s commit message contains a "WIP" or "DNM" tag, add the "wip" label and '
                    'to the issue remove other process labels such as "ready for review".\n'
                    '5. If no "WIP" or "DNM" tag is found in the change\'s commit message, add the "ready for review" '
                    'label to the issue and remove other process labels such as "ready for review".',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-g', '--gerrit-url', action='store', required=True, type=str,
                        default=os.getenv('GERRIT_URL', default=None), help='Target Gerrit URL.')
    parser.add_argument('-u', '--github-user', action='store', required=False, type=str,
                        default=os.getenv('GITHUB_USER', default=None),
                        help='Username to use for GitHub Issues integration. Defaults to GITHUB_USER in '
                             'environmental variables. Must be used with a password.')
    parser.add_argument('-p', '--github-password', action='store', required=False, type=str,
                        default=os.getenv('GITHUB_PW', default=None),
                        help='Password to use for GitHub Issues integration. Defaults to GITHUB_PW in '
                             'environmental variables. Must be used with a username.')
    parser.add_argument('-t', '--github-token', action='store', required=False, type=str,
                        default=os.getenv('GITHUB_TOKEN', default=None),
                        help='Token to use for GitHub Issues integration. Defaults to GITHUB_TOKEN in '
                             'environmental variables. This will be preferred over a username/password.')
    parser.add_argument('-v', '--verbose', action='store_true', required=False,
                        default=False, help='Enabled DEBUG level logging.')
    parser.add_argument('--log-file', action='store', required=False, type=str,
                        help='Specifies a file to output logs to. Defaults to `sys.stdout`.')
    parser.add_argument('gerrit_project_name', action='store', type=str, help='Target Gerrit project.')
    parser.add_argument('github_project_name', action='store', type=str, help='Target Github project.')
    ns = parser.parse_args()
    args = validate(ns)
    verbose = args.pop('verbose')
    log_file = args.pop('log_file')
    log_settings = {
        'format': LOG_FORMAT,
    }
    if verbose:
        log_settings['level'] = logging.DEBUG
    else:
        log_settings['level'] = logging.INFO
    if log_file:
        log_settings['filename'] = log_file
    else:
        log_settings['stream'] = sys.stdout
    logging.basicConfig(**log_settings)
    update(**args)
