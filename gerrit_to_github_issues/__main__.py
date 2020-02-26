# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import re
import sys

import github

GH_USER = sys.argv[1]
GH_PW = sys.argv[2]
ZUUL_MESSAGE = sys.argv[3]
GERRIT_URL = sys.argv[4]
REPO_NAME = 'airshipit/airshipctl'

if __name__ == '__main__':
    issue_number = re.search(r'(?<=\[#)(.*?)(?=\])', ZUUL_MESSAGE).group(0)
    gh = github.Github(GH_USER, GH_PW)
    repo = gh.get_repo(REPO_NAME)
    issue = repo.get_issue(number=int(issue_number))
    comment_msg = ''
    link_exists = False
    for comment in issue.get_comments():
        if GERRIT_URL in comment.body:
            logging.log(logging.INFO, 'Gerrit link has already been posted')
            link_exists = True
    if issue.state == 'closed' and not link_exists:
        issue.edit(state='open')
        comment_msg += 'Issue reopened due to new activity on Gerrit.\n\n'
    if 'WIP' in ZUUL_MESSAGE.upper() or 'DNM' in ZUUL_MESSAGE.upper():
        logging.log(logging.INFO, 'Changing status with `wip` label')
        issue.add_to_labels('wip')
        try:
            issue.remove_from_labels('ready for review')
        except github.GithubException:
            logging.log(logging.DEBUG, 'Could not remove `ready for review` label, '
                                       'it probably was not on the issue')
    else:
        logging.log(logging.INFO, 'Changing status with `ready for review` label')
        issue.add_to_labels('ready for review')
        try:
            issue.remove_from_labels('wip')
        except github.GithubException:
            logging.log(logging.DEBUG, 'Could not remove `wip` label, '
                                       'it probably was not on the issue')
    if not link_exists:
        comment_msg += f'New Related Change: {GERRIT_URL}'
    if comment_msg:
        issue.create_comment(comment_msg)
        logging.log(logging.INFO, f'Comment posted to issue #{issue_number}')