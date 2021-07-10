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
import json

from fabric import Connection


def get_changes(gerrit_url: str, project_name: str, port: int = 29418, change_age: str = None) -> list:
    cmd = f'gerrit query --format=JSON --current-patch-set project:{project_name}'
    if change_age:
        cmd += f' -- -age:{change_age}'
    result = Connection(gerrit_url, port=port).run(cmd)
    processed_stdout = '{"data":[%s]}' % ','.join(list(filter(None, result.stdout.split('\n'))))
    data = json.loads(processed_stdout)
    changes = [c for c in data['data'] if 'commitMessage' in c]
    return changes


def make_gerrit_url(gerrit_url: str, change_number: str, protocol: str = 'https'):
    return f'{protocol}://{gerrit_url}/{change_number}'
