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
import re

import github
from github.Issue import Issue
from github.Repository import Repository

import errors


def parse_issue_number(commit_msg: str) -> int:
    match = re.search(r'(?<=\[#)(.*?)(?=\])', commit_msg)
    if not match:
        return None
    return int(match.group(0))


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
