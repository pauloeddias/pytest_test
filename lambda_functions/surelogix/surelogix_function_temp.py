# Model config and description
model_info = {
    'model_name': "surelogix-compose-v26",
    'model_version': "v9",
    'model_meta_data': {
        'model_creator': "Paulo Silva",
        'latest_changes': {
            'v1': "Adding ALG and SBA",
            'v2': "Added Larson",
            'v3': "Pegasus HAWB added",
            'v4': "Custom Global added",
            'v5': "SBA DA added",
            'v6': "iCat HAWB added",
            'v7': "AllStates HAWB added",
            'v8': "Tazmanian added",
            'v9': "Larson updated to async (execution speed up)",
            'v10': "Added ACE Forwarding BOL",
            'v11': "Added Pegasus DA",
            'v12': "AirCareGo HAWB added",
            'v13': "Aeronet HAWB added",
            'v14': "iCat DA added",
            'v15': "Stevens DA DR added",
            'v16': "Allstates DA added",
            'v17': "Omni DA added",
            'v18': "Pegasus PickUpAlert added",
            'v19': "ALG PickUpAlert added",
        }
    }
}
import warnings
warnings.filterwarnings("ignore")

from .postprocessing._common import UnintendedFileException

import os
import base64
import asyncio
from PyPDF2 import PdfReader
import io
import json
import openai
import traceback

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

from .output_format_nested import slx_output_format as output_format
from .preprocessing.larson import SplitLarsonBase64
from .preprocessing.custom_global import CustomGlobalPreprocessor
from .preprocessing.stevens import SplitStevensBase64

from .postprocessing.custom_global import CustomGlobalPostprocessor
from .postprocessing.larson import LarsonExecutor
from .postprocessing.stevens_da_dr import StevensDaDrExecutor

from ._model_config import postprocessing_map


def read_document_with_azure(event):
    azure_endpoint = os.environ["AZURE_ENDPOINT"]
    azure_key = os.environ["AZURE_KEY"]
    doc_bytes = event["doc_bytes"]
    base64_bytes = doc_bytes.encode("utf8")
    message_bytes = base64.b64decode(base64_bytes)
    document_analysis_client = DocumentAnalysisClient(
        endpoint=azure_endpoint, credential=AzureKeyCredential(azure_key)
    )
    poller = document_analysis_client.begin_analyze_document('prebuilt-document', message_bytes)
    processed_result = poller.result()
    lines_content = []
    for line in processed_result.pages[0].lines:
        lines_content.append(line.content)
    first_page_text = '\n'.join(lines_content)

    return first_page_text, processed_result


def lambda_boilerplate(event, context, model_name):
    if os.getenv("ENVIRONMENT") == "dev":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    azure_endpoint = os.environ["AZURE_ENDPOINT"]
    azure_key = os.environ["AZURE_KEY"]
    openai.api_key = os.environ["OPENAI_API_KEY"]
    doc_bytes = event["doc_bytes"]
    base64_bytes = doc_bytes.encode("utf8")
    message_bytes = base64.b64decode(base64_bytes)

    document_analysis_client = DocumentAnalysisClient(
        endpoint=azure_endpoint, credential=AzureKeyCredential(azure_key)
    )
    poller = document_analysis_client.begin_analyze_document(model_name, message_bytes)
    docs = poller.result()

    ret = {}
    for name, field in docs.documents[0].fields.items():
        field_value = field.value if field.value else field.content
        ret[name] = field_value
    file_type = docs.documents[0].doc_type.split(':')[-1]
    return ret, file_type


def find_correct_preprocessor(event):
    buffer = base64.b64decode(event.get('doc_bytes'))
    f = io.BytesIO(buffer)
    pdf = PdfReader(f)

    preprocessor = None
    multi = False
    first_page = pdf.pages[0].extract_text().lower()

    if first_page:
        if 'LARSON MANUFACTURING COMPANY'.lower() in first_page:
            preprocessor = SplitLarsonBase64
            multi = True

        elif 'customgloballogistics' in first_page.replace(' ', ''):
            preprocessor = CustomGlobalPreprocessor

        elif 'stevensglobal' in first_page.replace(' ', '').lower():
            preprocessor = SplitStevensBase64(event)
            multi = len(pdf.pages) > 2
    else:
        # Need to analyze document with Azure
        first_page_text, processed_result = read_document_with_azure(event)

        if 'stevensglobal' in first_page_text.replace(' ', '').lower():
            preprocessor = SplitStevensBase64(event, processed_result)
            multi = len(pdf.pages) > 2

    return preprocessor, multi


def find_correct_postprocessor(doc_type):
    # Get postprocessing class by doc type
    postproc = postprocessing_map.get(doc_type, None)
    if postproc:
        return postproc
    else:
        raise Exception("No postprocessor found for doc_type: " + doc_type)


def lambda_core(event, context, model_name):
    ret, doc_type = lambda_boilerplate(event, context, model_name)
    postprocessor = find_correct_postprocessor(doc_type)
    postprocessor = postprocessor(ret, output_format)
    response = asyncio.run(postprocessor.run())
    return response, doc_type


def loop_executor_chain(preprocessor, event, context, model_name):
    doc_type = ''

    if preprocessor == SplitLarsonBase64:
        multi_docbytes = preprocessor(event).run()
        order_list, doc_type = asyncio.run(LarsonExecutor(multi_docbytes, output_format).run())

    elif type(preprocessor) == SplitStevensBase64:
        multi_docbytes = preprocessor.run()
        order_list, doc_type = asyncio.run(StevensDaDrExecutor(multi_docbytes, output_format).run())
    else:
        multi_docbytes = preprocessor(event).run()
        events_list = [{'doc_bytes': i} for i in multi_docbytes]
        order_list = []
        for event in events_list:
            order, doc_type = lambda_core(event, context, model_name)
            order_list.append(order)

    return order_list, doc_type


def general_executor_chain(preprocessor, event, context, model_name):
    order_list, doc_type = lambda_core(event, context, model_name)
    return order_list, doc_type


def custom_global_executor_chain(preprocessor, event, context, model_name):
    multi_docbytes = preprocessor(event).run()
    order_list, doc_type = asyncio.run(CustomGlobalPostprocessor(multi_docbytes, output_format).run())
    return order_list, doc_type


def get_executor_chain_type(preprocessor, multi):
    if preprocessor == CustomGlobalPreprocessor:
        return custom_global_executor_chain
    elif multi:
        return loop_executor_chain
    else:
        return general_executor_chain


def lambda_handler(event, context=None):
    model_name = model_info.get('model_name')

    try:
        preprocessor, multi = find_correct_preprocessor(event)
        executor_chain = get_executor_chain_type(preprocessor, multi)
        order_list, doc_type = executor_chain(preprocessor, event, context, model_name)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "order_list": order_list
            }),
            'customer_info': {
                'customer': 'surelogix',
                'tms': 'crown',
                'sub_customer': doc_type.split('-')[-2],
            },
            'model_info': model_info,
            'file_type':"blfp",
            }
            
    except UnintendedFileException as e:
        return {
            "statusCode": 406,
            "headers": {
                "Content-Type": "application/json"
            },
            "errorMessage": "File type not supported"
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "errorMessage": traceback.format_exc()
        }
