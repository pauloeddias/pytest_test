import glob
import base64
import json
import os
import pandas as pd
import boto3
from botocore.client import Config
from datetime import datetime
from deepdiff import DeepDiff

# TODO Please change import location to the required project
#  Ex: analyze_output can be user from src/evaluation/eval_engine.py
from lambda_functions.surelogix.surelogix_function_temp import lambda_handler


## ------------------------------------
# Please Chose tests (Local or lambda in bottom of file)
## ------------------------------------


# TODO Please Set the main config for testing (if it needed)
current_path = os.path.dirname(os.path.realpath(__file__))
expected_s3_prefix = "surelogix/alg_pu/"                             # set the Directory on S3 whe the expected json files placed (or live '' if it is not needed)
test_docs_path = os.path.join(current_path, 'test_docs')                # set path to the test docs folder
folder_path = os.path.join(test_docs_path, 'input')                     # set path to the input files folder
output_folder = os.path.join(test_docs_path, 'output')                  # output results_folder
analysis_folder = os.path.join(test_docs_path, 'analysis')              # analytics results folder
lambda_project_name = "DML_PROD_surelogix_secondary"                  # Lambda name that should be tested
# lambda_project_name = "DML_STAGING_surelogix"                      # Lambda name that should be tested


def count_fields(d):
    if type(d) is dict:
        return sum([count_fields(v) for v in d.values()])
    elif type(d) is list:
        return sum([count_fields(v) for v in d])
    else:
        return 1


def s3_get_files(prefix, file_name):
    s3 = boto3.resource("s3")
    bucket = s3.Bucket("dml-test-files")
    for obj in bucket.objects.filter(Prefix=prefix):
        if obj.key.endswith(".json") and file_name in obj.key:
            return obj.get()["Body"].read()
    return None


def data_extraction_analytics(file_name, extracted_data):
    analytics_data = {
        'diffs': [],
        'summary': {}
    }

    expected_file = s3_get_files(expected_s3_prefix, file_name)
    if expected_file:
        expected = json.loads(expected_file)
        diff = DeepDiff(expected, extracted_data, view="tree").to_dict()

        set_of_values_changed = diff.get('values_changed', [])
        if set_of_values_changed:
            for changed in set_of_values_changed:
                analytics_data['diffs'].append({
                    'path': changed.path(),
                    'expected': changed.t1,
                    'actual': changed.t2
                })

        set_of_types_changed = diff.get('type_changes', [])
        if set_of_types_changed:
            for changed in set_of_types_changed:
                analytics_data['diffs'].append({
                    'path': changed.path(),
                    'expected': changed.t1,
                    'actual': changed.t2
                })

        num_diffs = sum([len(diff[x]) for x in diff])
        num_fields = count_fields(expected)
        analytics_data['summary'].update({
            'num_diffs': num_diffs,
            'num_fields': num_fields,
            'num_correct': num_fields - num_diffs,
            'accuracy': round((num_fields - num_diffs) / num_fields, 2)
        })
    return analytics_data


def local_tests():
    print('LOCAL TESTING')
    # TODO: For the local testing create and place test files to the "test_docs/input" directory in current project directory.
    #  Ex: "blkout/test_docs/input/<HAWBDelivery_pdf_files>"
    #  the output files will be placed in "test_docs/output"
    #  the analytics csv result will be placed in "test_docs/analysis folder"

    pdf_files = glob.glob(folder_path + "/*.pdf")
    pdf_paths = []

    print("# of files tested: ", len(pdf_files))

    if pdf_files:
        analysis_data = pd.DataFrame(columns=['file_name', 'scac', 'shipment_identifier', 'num_correct', 'num_fields', 'accuracy'])

        for pdf_path in pdf_files:
            pdf_paths.append(pdf_path)

        for pdf_path in sorted(pdf_paths):
            pdf_name = pdf_path.split(os.sep)[-1].replace('.pdf', '')

            with open(pdf_path, "rb") as file:
                form = file.read()

            base64_bytes = base64.b64encode(form)
            base64_message = base64_bytes.decode("utf8")
            event = {'doc_bytes': base64_message}
            print('Tested file: ', pdf_name)
            exec_start_time = datetime.now()
            print('Start time', exec_start_time)
            res = lambda_handler(event, None)
            exec_end_time = datetime.now()
            exec_time = str(exec_end_time - exec_start_time)
            print('End Time', exec_end_time)
            print('Exec Time', exec_time)
            res.update({
                'execution_time': exec_time
            })
            if res.get('body'):
                body = json.loads(res.get('body'))
                res.update({'body': body})

            # Write JSON to file
            os.makedirs(output_folder, exist_ok=True)
            output_file_path = os.path.join(output_folder, pdf_name + ".json")

            orders_data = res.get('body', {}).get('order_list', [])
            if type(orders_data) is dict:
                orders_data = [orders_data]

            # For now analytics working for single order result
            output_analytics = {}
            if orders_data:
                output_analytics = data_extraction_analytics(pdf_name, orders_data[0])
                if output_analytics:
                    res.update({
                        'analytics': output_analytics
                    })

            for order in orders_data:
                print('\n')
                new_row = {
                    'file_name': pdf_name,
                    "scac": order.get('scac'),
                    "shipment_identifier": order.get('shipment_identifier'),
                    'num_correct': output_analytics.get('summary', {}).get('num_correct'),
                    'num_fields': output_analytics.get('summary', {}).get('num_fields'),
                    'accuracy': output_analytics.get('summary', {}).get('accuracy'),
                }
                analysis_data.loc[len(analysis_data)] = new_row
                for k, v in new_row.items():
                    print(k, v)

                print("\n\n")

            with open(output_file_path, "w") as file:
                json.dump(res, file, indent=4)

        os.makedirs(analysis_folder, exist_ok=True)

        analysis_file_path = os.path.join(analysis_folder, 'analysis' + ".csv")
        # Need to count avg values
        new_row = {
            'file_name': 'AVERAGE ACCURACY',
            "scac": '--',
            "shipment_identifier": "--",
            'num_correct': "--",
            'num_fields': "--",
            'accuracy': round(analysis_data['accuracy'].sum() / analysis_data['accuracy'].count(), 2),
        }
        analysis_data.loc[len(analysis_data)] = new_row
        with open(analysis_file_path, "w") as file:
            analysis_data.to_csv(file, index=False)


def invoke_lambda(function_name, payload):
    config = Config(read_timeout=900)
    client = boto3.client("lambda", config=config)
    response = client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    return json.loads(response["Payload"].read().decode("utf-8"))


def lambda_tests():
    print('LAMBDA TESTING')
    # TODO: For the local testing create and place test files to the "test_docs/input" directory in current project directory.
    #  Ex: "blkout/test_docs/input/<HAWBDelivery_pdf_files>"
    #  the output files will be placed in "test_docs/output"
    #  the analytics csv result will be placed in "test_docs/analysis folder"

    # TODO Set you project lambda name
    #  aws cli account should be configured for IDE

    pdf_files = glob.glob(folder_path + "/*.pdf")
    pdf_paths = []

    print("# of files tested: ", len(pdf_files))

    if pdf_files:

        analysis_data = pd.DataFrame(columns=['file_name', 'scac', 'shipment_identifier', 'num_correct', 'num_fields', 'accuracy'])

        for pdf_path in pdf_files:
            pdf_paths.append(pdf_path)

        for pdf_path in sorted(pdf_paths):
            pdf_name = pdf_path.split(os.sep)[-1].replace('.pdf', '')

            with open(pdf_path, "rb") as file:
                form = file.read()

            base64_bytes = base64.b64encode(form)
            base64_message = base64_bytes.decode("utf8")
            event = {'doc_bytes': base64_message}
            print('Tested file: ', pdf_name)

            exec_start_time = datetime.now()
            res = invoke_lambda(lambda_project_name, event)
            exec_end_time = datetime.now()
            res.update({
                'execution_time': str(exec_end_time - exec_start_time)
            })

            if res.get('body'):
                body = json.loads(res.get('body'))
                res.update({'body': body})

            # Write JSON to file
            output_folder = os.path.join(test_docs_path, 'output')
            os.makedirs(output_folder, exist_ok=True)
            output_file_path = os.path.join(output_folder, pdf_name + ".json")

            orders_data = res.get('body', {}).get('order_list', [])
            if type(orders_data) is dict:
                orders_data = [orders_data]

            # For now analytics working for single order result
            output_analytics = {}
            if orders_data:
                output_analytics = data_extraction_analytics(pdf_name, orders_data[0])
                if output_analytics:
                    res.update({
                        'analytics': output_analytics
                    })

            for order in res.get('body', {}).get('order_list', []):
                print('\n')
                new_row = {
                    'file_name': pdf_name,
                    "scac": order.get('scac'),
                    "shipment_identifier": order.get('shipment_identifier'),
                    'num_correct': output_analytics.get('summary', {}).get('num_correct'),
                    'num_fields': output_analytics.get('summary', {}).get('num_fields'),
                    'accuracy': output_analytics.get('summary', {}).get('accuracy'),
                }
                analysis_data.loc[len(analysis_data)] = new_row
                for k, v in new_row.items():
                    print(k, v)
                print("\n\n")

            with open(output_file_path, "w") as file:
                json.dump(res, file, indent=4)
            print('execution_time', str(exec_end_time - exec_start_time))

        analysis_folder = os.path.join(test_docs_path, 'analysis')
        os.makedirs(analysis_folder, exist_ok=True)
        # Need to count avg values
        new_row = {
            'file_name': 'AVERAGE ACCURACY',
            "scac": '--',
            "shipment_identifier": "--",
            'num_correct': "--",
            'num_fields': "--",
            'accuracy': round(analysis_data['accuracy'].sum() / analysis_data['accuracy'].count(), 2),
        }
        analysis_data.loc[len(analysis_data)] = new_row

        analysis_file_path = os.path.join(analysis_folder, 'lambda_analysis' + ".csv")
        with open(analysis_file_path, "w") as file:
            analysis_data.to_csv(file, index=False)


# Chose target tests
if __name__ == "__main__":
    # lambda_tests()
    local_tests()

