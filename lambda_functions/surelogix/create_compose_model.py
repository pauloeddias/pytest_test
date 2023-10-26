import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentModelAdministrationClient


if __name__ == '__main__':
    azure_endpoint = os.environ["AZURE_ENDPOINT"]
    azure_key = os.environ["AZURE_KEY"]

    form_training_client = DocumentModelAdministrationClient(endpoint=azure_endpoint, credential=AzureKeyCredential(azure_key))

    models_trained_with_labels = [
        'surelogix-am-alg-v1',
        'surelogix-da-teamworldwide-v2',
        'surelogix-da-dba-v4',
        'surelogix-da-trumpcard-v5',
        'surelogix-sba-v2',
        'surelogix-hw-omni-v2',  # toDo was added in task [ENG-487] Investigate and address dimensions for all Surelogix sub customers - Group 1, need create new compose
        'surelogix-mrgpod-larson-v1',
        'surelogix-dr-sba-v4',
        'surelogix-da-sba-v2',
        'surelogix-hawb-allstates-v3',
        'surelogix-hawb-icat-v2',
        "surelogix-da-tazmanian-v1",
        "surelogix-bol-aceforwarding-v1",
        "surelogix-da-pegasus-v4",
        # 'surelogix-da-taif-v3',  # this model is not needed "surelogix-da-teamworldwide-v2" used instead
        "surelogix-hawb-aircarego-v3",
        "surelogix-hawb-aeronet-v6",
        "surelogix-da-icat-v3",
        "surelogix-da-dr-stevens-v6",
        "surelogix-da-allstates-v3",
        "surelogix-da-omni-v5",
        "surelogix-pickupalert-pegasus-v3",
        "surelogix-pu-alg-v3",
        "surelogix-pickupalert-dba-v2",
        'surelogix-hawb-pegasus-v1'
    ]

    models_in_production = [
        'surelogix-am-alg-v1',
        'surelogix-sba-v2',
        'surelogix-mrgpod-larson-v1',
        'surelogix-da-dba-v4',
        "surelogix-da-dr-stevens-v6",
        'surelogix-da-trumpcard-v5',
        "surelogix-da-tazmanian-v1",
        'surelogix-hw-omni-v2',  # toDo was added in task [ENG-487] Investigate and address dimensions for all Surelogix sub customers - Group 1, need create new compose
        'surelogix-hawb-pegasus-v1'
    ]

    poller = form_training_client.begin_compose_document_model(
        models_in_production,
        model_id="surelogix-compose-v31",
        description="https://www.notion.so/DML-Model-Matrix-333f3b0731164340b65b3b629950da41"
    )
    model = poller.result()
    print(model)
