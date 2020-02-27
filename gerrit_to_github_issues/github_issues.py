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
import re

import github
from github.Issue import Issue
from github.Repository import Repository

from gerrit_to_github_issues import errors

LOG = logging.getLogger(__name__)


def construct_issue_list(match_list: list) -> list:
    new_list = []
    for issue in match_list:
        try:
            new_list.append(int(issue))
        except ValueError:
            LOG.warning(f'Value {issue} could not be converted to `int` type')
    return new_list


def parse_issue_number(commit_msg: str) -> dict:
    # Searches for Relates-To or Closes tags first to match and return
    LOG.debug(f'Parsing commit message: {commit_msg}')
    related = re.findall(r'(?<=Relates-To: #)(.*?)(?=\n)', commit_msg)
    LOG.debug(f'Captured related issues: {related}')
    closes = re.findall(r'(?<=Closes: #)(.*?)(?=\n)', commit_msg)
    LOG.debug(f'Captured closes issues: {closes}')
    if related or closes:
        return {
            'related': construct_issue_list(related),
            'closes': construct_issue_list(closes)
        }
    # If no Relates-To or Closes tags are defined, find legacy [#X] style tags
    LOG.debug('Falling back to legacy tags')
    legacy_matches = re.findall(r'(?<=\[#)(.*?)(?=\])', commit_msg)
    LOG.debug(f'Captured legacy issues: {legacy_matches}')
    if not legacy_matches:
        return {}
    return {
        'related': construct_issue_list(legacy_matches)
    }


def remove_duplicated_issue_numbers(issue_dict: dict) -> dict:
    if 'closes' in issue_dict:
        issue_dict['related'] = [x for x in issue_dict['related'] if x not in issue_dict['closes']]
    return issue_dict


def get_repo(repo_name: str, github_user: str, github_pw: str, github_token: str) -> Repository:
    if github_token:
        gh = github.Github(github_token)
    elif github_user and github_pw:
        gh = github.Github(github_user, github_pw)
    else:
        raise errors.GithubConfigurationError
    return gh.get_repo(repo_name)


def check_issue_for_matching_comments(issue: Issue, contains: str) -> bool:
    for comment in issue.get_comments():
        if contains in comment.body:
            return True
    return False
