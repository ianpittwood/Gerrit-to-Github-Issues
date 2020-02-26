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
import logging

import github
from github.Repository import Repository

import gerrit
import github_issues

LOG = logging.getLogger(__name__)


def update(gerrit_url: str, gerrit_project_name: str, github_project_name: str, github_user: str, github_password: str,
           github_token: str):
    repo = github_issues.get_repo(github_project_name, github_user, github_password, github_token)
    change_list = gerrit.get_changes(gerrit_url, gerrit_project_name)
    for change in change_list['data']:
        if 'commitMessage' in change:
            process_change(change, repo, gerrit_url)


def process_change(change: dict, repo: Repository, gerrit_url: str):
    issue_number = github_issues.parse_issue_number(change['commitMessage'])
    if not issue_number:
        LOG.warning(f'No issue tag found for change #{change["number"]}')
        return
    try:
        issue = repo.get_issue(issue_number)
    except github.GithubException:
        LOG.warning(f'Issue #{issue_number} not found for project')
        return
    comment_msg = ''
    change_url = gerrit.make_gerrit_url(gerrit_url, change['number'])
    link_exists = github_issues.check_issue_for_matching_comments(issue, change_url)
    if issue.state == 'closed' and not link_exists:
        issue.edit(state='open')
        comment_msg += 'Issue reopened due to new activity on Gerrit.\n\n'
    if 'WIP' in change['commitMessage'] or 'DNM' in change['commitMessage']:
        LOG.debug(f'add `wip` to #{issue_number}')
        issue.add_to_labels('wip')
        try:
            LOG.debug(f'rm `ready for review` to #{issue_number}')
            issue.remove_from_labels('ready for review')
        except github.GithubException:
            LOG.debug(f'`ready for review` tag does not exist on issue #{issue_number}')
    else:
        LOG.debug(f'add `ready for review` to #{issue_number}')
        issue.add_to_labels('ready for review')
        try:
            LOG.debug(f'rm `wip` to #{issue_number}')
            issue.remove_from_labels('wip')
        except github.GithubException:
            LOG.debug(f'`wip` tag does not exist on issue #{issue_number}')
    if not link_exists:
        comment_msg += f'New Related Change: {change_url}\n' \
                       f'Authored By: {change["owner"]["name"]} ({change["owner"]["email"]})'
    if comment_msg:
        issue.create_comment(comment_msg)
        LOG.debug(f'Comment to post on #{issue_number}: {comment_msg}')
        LOG.info(f'Comment posted to issue #{issue_number}')
