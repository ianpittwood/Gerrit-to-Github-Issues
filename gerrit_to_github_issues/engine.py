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
import datetime
import logging

import github
import pytz as pytz
from github.Repository import Repository
from github.Project import Project
from github.Issue import Issue

from gerrit_to_github_issues import gerrit
from gerrit_to_github_issues import github_issues

LOG = logging.getLogger(__name__)


def update(gerrit_url: str, gerrit_repo_name: str, github_project_id: int,
           github_repo_name: str, github_user: str, github_password: str, github_token: str,
           change_age: str = None, skip_approvals: bool = False):
    gh = github_issues.get_client(github_user, github_password, github_token)
    repo = gh.get_repo(github_repo_name)
    project_board = gh.get_project(github_project_id)
    change_list = gerrit.get_changes(gerrit_url, gerrit_repo_name, change_age=change_age)
    for change in change_list['data']:
        if 'commitMessage' in change:
            process_change(gh, change, repo, project_board, skip_approvals)

    # Handle the incoming issue assignment requests
    github_issues.assign_issues(repo)


def process_change(gh: github.Github, change: dict, repo: Repository,
                   project_board: Project, skip_approvals: bool = False):
    issue_numbers_dict = github_issues.parse_issue_number(change['commitMessage'])
    issue_numbers_dict = github_issues.remove_duplicated_issue_numbers(issue_numbers_dict)
    if not issue_numbers_dict:
        LOG.warning(f'No issue tag found for change #{change["number"]}')
        return
    for key, issues_list in issue_numbers_dict.items():
        for issue_number in issues_list:
            try:
                issue = repo.get_issue(issue_number)
            except github.GithubException:
                LOG.warning(f'Issue #{issue_number} not found for project')
                return
            bot_comment = github_issues.get_bot_comment(issue, gh.get_user().login, change['number'])
            if issue.state == 'closed' and not bot_comment:
                LOG.debug(f'Issue #{issue_number} was closed, reopening...')

                # NOTE(howell): Reopening a closed issue will move it from the
                # "Done" column to the "In Progress" column on the project
                # board via Github automation.
                issue.edit(state='open')
                issue.create_comment('Issue reopened due to new activity on Gerrit.\n\n')

            labels = [str(l.name) for l in list(issue.get_labels())]
            if 'WIP' in change['commitMessage'] or 'DNM' in change['commitMessage']:
                if 'wip' not in labels:
                    LOG.debug(f'add `wip` to #{issue_number}')
                    issue.add_to_labels('wip')
                if 'ready for review' in labels:
                    try:
                        LOG.debug(f'rm `ready for review` to #{issue_number}')
                        issue.remove_from_labels('ready for review')
                    except github.GithubException:
                        LOG.debug(f'`ready for review` tag does not exist on issue #{issue_number}')
                move_issue(project_board, issue, 'In Progress')
            else:
                if 'ready for review' not in labels:
                    LOG.debug(f'add `ready for review` to #{issue_number}')
                    issue.add_to_labels('ready for review')
                if 'wip' in labels:
                    try:
                        LOG.debug(f'rm `wip` to #{issue_number}')
                        issue.remove_from_labels('wip')
                    except github.GithubException:
                        LOG.debug(f'`wip` tag does not exist on issue #{issue_number}')
                move_issue(project_board, issue, 'Submitted on Gerrit')
            comment_msg = get_issue_comment(change, key, skip_approvals)
            if not bot_comment:
                if key == 'closes':
                    comment_msg += '\n\nThis change will close this issue when merged.'
                LOG.debug(f'Comment to post on #{issue_number}: {comment_msg}')
                issue.create_comment(comment_msg)
                LOG.info(f'Comment posted to issue #{issue_number}')
            else:
                LOG.debug(f'Comment to edit on #{issue_number}: {comment_msg}')
                comment = github_issues.get_bot_comment(issue, gh.get_user().login, change['number'])
                comment.edit(comment_msg)
                LOG.info(f'Comment edited to issue #{issue_number}')


def get_issue_comment(change: dict, key: str, skip_approvals: bool = False) -> str:
    comment_str = f'## Related Change [#{change["number"]}]({change["url"]})\n\n' \
                  f'**Subject:** {change["subject"]}\n' \
                  f'**Link:** {change["url"]}\n' \
                  f'**Status:** {change["status"]}\n' \
                  f'**Owner:** {change["owner"]["name"]} ({change["owner"]["email"]})\n\n'
    if key == 'closes':
        comment_str += 'This change will close this issue when merged.\n\n'
    if not skip_approvals:
        comment_str += '### Approvals\n' \
                       '```diff\n'

        approval_dict = {
            'Code-Review': [],
            'Verified': [],
            'Workflow': []
        }
        if 'approvals' in change['currentPatchSet']:
            for approval in change['currentPatchSet']['approvals']:
                if approval['type'] in approval_dict:
                    approval_dict[approval['type']].append((approval['by']['name'], approval['value']))
                else:
                    LOG.warning(f'Approval type "{approval["type"]}" is not a known approval type')

        for key in ['Code-Review', 'Verified', 'Workflow']:
            comment_str += f'{key}\n'
            if approval_dict[key]:
                for approval in approval_dict[key]:
                    if int(approval[1]) > 0:
                        comment_str += '+'
                    comment_str += f'{approval[1]} {approval[0]}\n'
            else:
                comment_str += '! None\n'
        comment_str += '```'
    dt = datetime.datetime.now(pytz.timezone('America/Chicago')).strftime('%Y-%m-%d %H:%M:%S %Z').strip()
    comment_str += f'\n\n*Last Updated: {dt}*'
    return comment_str


def move_issue(project_board: Project, issue: Issue, to_col_name: str):
    to_col, card = None, None
    for col in project_board.get_columns():
        if col.name == to_col_name:
            to_col = col
        else:
            for c in col.get_cards():
                if c.get_content() == issue:
                    card = c

    if not to_col:
        LOG.warning(f'Column with name "{to_col_name}" could not be found for project "{project_board.name}"')
        return

    if not card:
        LOG.warning(f'Issue with name "{issue.name}" could not be found for project "{project_board.name}"')
        return

    if card.move("top", to_col):
        LOG.info(f'Moved issue "{issue.name}" to column "{to_col_name}"')
    else:
        LOG.warning(f'Failed to move issue "{issue.name}" to column "{to_col_name}"')
