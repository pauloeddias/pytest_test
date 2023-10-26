from .BaseTest import BaseTest
import json
from ..surelogix_function_temp import lambda_handler
import base64
from deepdiff import DeepDiff


class StevensTest(BaseTest):
    def parse_files(self,args):
        response_file = args[1]
        form = args[0]
        # file_name = args[2]

        base64_bytes = base64.b64encode(form)
        base64_message = base64_bytes.decode("utf8")

        event = {"doc_bytes": base64_message}

        response = lambda_handler(event, None)
        response = json.loads(response.get('body', '{}')).get('order_list', {})

        # if os.getenv("ENVIRONMENT") == "dev":
        #     # response = json.loads(response)
        #     json.dump(response, open("lambda_functions/surelogix/files/ALG/" + file_name + "_response.json", "w"), indent=1)

        expected = json.loads(response_file)

        diff = DeepDiff(expected, response, view="tree")

        diffs = sum([len(diff[x]) for x in diff])
        num_fields = self.count_fields(expected)

        return num_fields - diffs, num_fields

def test_stevens_da_dr():
    files_path = "surelogix/stevens_da_dr/"
    test = StevensTest(files_path)
    print('Result', test.res)
    return test.res
