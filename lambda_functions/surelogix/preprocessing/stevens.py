import os
import io
import base64
import re

from PyPDF2 import PdfWriter, PdfReader, PageObject, PdfFileReader, Transformation
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential


IS_LOCAL = eval(os.getenv('IS_LOCAL', 'False'))


class SplitStevensBase64:
    def __init__(self, event, processed_result=None):
        self.doc_bytes = event.get('doc_bytes')
        base64_bytes = self.doc_bytes.encode("utf8")
        self.base64_message = base64_bytes.decode("utf8")
        message_bytes = base64.b64decode(base64_bytes)

        # For development need to place split files to test directory
        if IS_LOCAL:
            self.tmp_dir = os.path.join(os.getcwd(), 'test_docs/tmp')
        else:
            self.tmp_dir = '/tmp'

        if not processed_result:
            # Extract data with Asure
            model_name = "prebuilt-document"
            document_analysis_client = DocumentAnalysisClient(
                endpoint=os.environ["AZURE_ENDPOINT"],
                credential=AzureKeyCredential(os.environ["AZURE_KEY"]),
            )
            poller = document_analysis_client.begin_analyze_document(model_name, message_bytes)
            self.docs = poller.result()
        else:
            self.docs = processed_result

    def run(self):
        buffer = base64.b64decode(self.base64_message)
        f = io.BytesIO(buffer)
        pdf = PdfReader(f)
        b64 = []
        receipt_pages = []
        alert_pages = {}

        # Need to check first_page file type Alert or receipt
        dock_type = 'receipt'
        for ind, line in enumerate(self.docs.pages[0].lines):
            if 'Alert!' in line.content:
                dock_type = 'alert'

        # for page in self.docs.pages:
        #     for ind, line in enumerate(page.lines):
        #         if 'WAYBILL #' in line.content:
        #             print('KEY', line.content)
        #             print('WAYBILL #', page.lines[ind + 1].content)
        #             print('WAYBILL #', page.lines[ind + 2].content)
        #             print('WAYBILL #', page.lines[ind + 3].content)

        if dock_type == 'alert':
            mawb = None
            for i in self.docs.key_value_pairs:
                # need to find order_identifier Mawb
                if 'mawb' in i.key.content.lower():
                    mawb = i.value.content if i.value else None
                    if mawb not in alert_pages.keys():
                        alert_pages.update({
                            mawb: {
                                'page': [region.page_number for region in i.key.bounding_regions],
                                'waybills': []
                            }
                        })

            for i in self.docs.key_value_pairs:
                if 'Container Number' in i.key.content:
                    polygon = [region.polygon for region in i.key.bounding_regions][0]
                    min_y = min([i.y for i in polygon])

                    if mawb and alert_pages.get(mawb):
                        alert_pages[mawb]['waybills'].append({
                            'page': [region.page_number for region in i.key.bounding_regions][0],
                            'min_y': min_y
                        })

        for i in self.docs.key_value_pairs:
            # Need to build logic to Convert PDF
            if 'WAYBILL NO' in i.key.content:
                order_id = i.value.content if i.value else None
                if order_id:
                    # need to clean order_id
                    match = re.search(r'\*\d{4,10}\*', order_id)
                    if match:
                        order_id = match.group(0)

                        receipt_obj = [i for i in receipt_pages if i.get('waybill_number') == order_id]
                        if receipt_obj:
                            page_number = [region.page_number for region in i.key.bounding_regions][0]
                            if page_number not in receipt_obj[0]['pages']:
                                receipt_obj[0]['pages'].append(page_number)
                        else:
                            receipt_pages.append({
                                'waybill_number': order_id,
                                'pages': [region.page_number for region in i.key.bounding_regions]
                            })
                        # # Update condition to check in list
                        # if order_id not in order_pages.keys():
                        #     receipt_pages_pages.update({order_id: []})
                        # order_pages[order_id].extend([region.page_number for region in i.key.bounding_regions])

        if alert_pages.items():
            print('IF')
            for k, v in alert_pages.items():
                main_pdf = PdfReader(f)

                # Prepare the first page data
                first_page = main_pdf.pages[0]
                waybills_items = v.get('waybills', [])

                # The bottom border of main info it is start first waybill block
                bottom_y = waybills_items[0].get('min_y')
                main_page = self.transform_main_page(first_page, bottom_y=bottom_y)

                for index, waybill in enumerate(waybills_items):
                    internal_pdf = PdfReader(f)

                    pdf_writer = PdfWriter()
                    output_filename = f"{self.tmp_dir}/order_{k}_{index}.pdf"
                    waybill_page_number = waybill.get('page')
                    waybill_page = internal_pdf.pages[waybill_page_number - 1]

                    top_y = waybill.get('min_y', 0)
                    try:
                        next_waybill = waybills_items[index + 1]
                        if next_waybill.get('page') == waybill_page_number:
                            bottom_y = next_waybill.get('min_y')
                        else:
                            bottom_y = None
                    except:
                        bottom_y = None

                    waybill_page_block = self.transform_internal_page(
                        waybill_page,
                        top_y,
                        bottom_y
                    )

                    # Logic to merge blocks to single page
                    # But Asure extract data incorrectly (hidden data contains on the page)
                    # Merge the transformed page onto the output page
                    # single_page = PageObject.create_blank_page(
                    #     pdf=None,
                    #     height=page_height,
                    #     width=page_width
                    # )
                    # single_page.merge_page(main_page)
                    # single_page.merge_page(waybill_page_block)
                    # pdf_writer.add_page(single_page)

                    # Write result to the new PDF (pdf blocks will contains in the separate pages)
                    pdf_writer.add_page(main_page)
                    pdf_writer.add_page(waybill_page_block)

                    # TODO Need to check if order_pages.items() need to add Receipt pages
                    #  need to convert orders from dict to list
                    #  and working with indexes
                    if receipt_pages:
                        receipt = receipt_pages[index]
                        print('receipt')
                        print(receipt)
                        for page_num in receipt.get('pages'):
                            pdf_writer.add_page(pdf.pages[page_num - 1])

                    with open(output_filename, "wb") as out:
                        pdf_writer.write(out)

                    with open(output_filename, "rb") as file:
                        form = file.read()

                    base64_bytes = base64.b64encode(form)
                    base64_message = base64_bytes.decode("utf8")
                    b64.append(base64_message)

                    if not IS_LOCAL:
                        # delete the file output_filename
                        os.remove(output_filename)

        elif receipt_pages:
            print('ELIF')
            for receipt in receipt_pages:
                pdf_writer = PdfWriter()
                for page_num in receipt.get('pages'):
                    pdf_writer.add_page(pdf.pages[page_num-1])

                output_filename = f"{self.tmp_dir}/order_{receipt.get('waybill_number')}.pdf"

                with open(output_filename, "wb") as out:
                    pdf_writer.write(out)

                with open(output_filename, "rb") as file:
                    form = file.read()

                base64_bytes = base64.b64encode(form)
                base64_message = base64_bytes.decode("utf8")
                b64.append(base64_message)

                if not IS_LOCAL:
                    # delete the file output_filename
                    os.remove(output_filename)
        else:
            print('# In case if Doc can be split return full pdf')
            # In case if Doc can be split return full pdf
            b64.append(self.base64_message)

        return b64

    def transform_main_page(self, page, top_y=None, bottom_y=None):
        self.page_height = page.mediabox.height
        self.page_width = page.mediabox.width

        # # Determine the upper and lower bounds for the crop
        upper_bound = self.page_height

        # Distance from bottom of the document to y (pyPDF count distance from bottom to top)
        # And need to convert Azure inch to points i inch = 72 points
        distance = self.page_height - (bottom_y * 72)
        self.main_bottom_bound = distance

        # Calculate the translation to apply to the page
        y_translation = self.page_height - upper_bound

        # Create a transformation object with the calculated translation
        transformation = Transformation().translate(ty=y_translation)
        # Apply the transformation to the page
        page.add_transformation(transformation)

        # Update the page media box with the new bounds
        page.mediabox.lower_left = (0, self.main_bottom_bound + y_translation)
        page.mediabox.upper_right = (self.page_width, upper_bound + y_translation)

        return page

    def transform_internal_page(self, page, top_y, bottom_y):
        # # Determine the upper and lower bounds for the crop
        upper_bound = self.page_height - (top_y * 72)
        bottom_bound = self.page_height - (bottom_y * 72) if bottom_y else 0

        # Calculate the translation to apply to the page
        # w_y_translation = page_height - lower_bound - w_upper_bound - 70
        # Worked row 70 - divider points (Not find tmp, currently not required)
        w_y_translation = self.page_height - self.main_bottom_bound - upper_bound

        # Create a transformation object with the calculated translation
        w_y_transformation = Transformation().translate(ty=w_y_translation)
        # Apply the transformation to the page
        page.add_transformation(w_y_transformation)

        # Update the page media box with the new bounds
        page.mediabox.lower_left = (0, bottom_bound + w_y_translation)
        page.mediabox.upper_right = (self.page_width, upper_bound + w_y_translation)

        return page


'''

Example that was taken for implementation

from PyPDF2 import PageObject, PdfFileReader, PdfFileWriter, Transformation

# Define the crop bounds for pages other than the first page
CROP_Y_TOP = 556
CROP_Y_HEIGHT = 482

# Set the input and output file paths
input_path = r"input.pdf"
output_path = r"output.pdf"

# Open the input and output files in binary read and write mode
with open(input_path, "rb") as input_file, open(output_path, "wb") as output_file:
    # Create a PdfFileReader object for the input file
    reader = PdfFileReader(input_file)
    # Create a PdfFileWriter object for the output file
    writer = PdfFileWriter()

    # Calculate the total height of the output page
    total_height = reader.getPage(0).mediabox.height + (CROP_Y_HEIGHT * (reader.getNumPages() - 1))

    # Create a blank page with the calculated total height
    single_page = PageObject.create_blank_page(
        pdf=None,
        width=reader.getPage(0).mediabox.width,
        height=total_height
    )

    # Loop through all pages of the input document
    for i in range(reader.getNumPages()):
        # Get the current page
        page = reader.getPage(i)
        original_mediabox = reader.getPage(i).mediaBox

        # Determine the upper and lower bounds for the crop
        upper_bound = original_mediabox.height if i == 0 else CROP_Y_TOP
        lower_bound = 0 if i == 0 else CROP_Y_TOP - CROP_Y_HEIGHT

        # Calculate the translation to apply to the page
        y_translation = total_height - upper_bound

        # Create a transformation object with the calculated translation
        transformation = Transformation().translate(ty=y_translation)
        # Apply the transformation to the page
        page.add_transformation(transformation)

        # Update the page media box with the new bounds
        page.mediabox.lower_left = (0, lower_bound + y_translation)
        page.mediabox.upper_right = (original_mediabox.width, upper_bound + y_translation)

        print(f"T={y_translation}\tU={upper_bound + y_translation}\tL={lower_bound + y_translation}")

        # Merge the transformed page onto the output page
        single_page.merge_page(page)

        # Decrease the total height by the height of the current page
        total_height -= upper_bound

    # Add the output page to the writer
    writer.addPage(single_page)

    # Write the output file
    writer.write(output_file)

'''
