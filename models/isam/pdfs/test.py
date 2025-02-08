import zipfile
import os
from PyPDF2 import PdfReader
import re

# Function to read PDF pages
def read_pdf_pages(pdf_path, num_pages=1):
    pdf_text = []
    with open(pdf_path, 'rb') as f:
        pdf_reader = PdfReader(f)
        for page_num in range(min(num_pages, pdf_reader.pages)):
            page = pdf_reader.getPage(page_num)
            pdf_text.append(page.extractText())
    return pdf_text

# Function to parse command tree from text
def parse_command_tree(text):
    command_tree_start = text.find("CommandTree")
    if command_tree_start == -1:
        return "CommandTree not found in text."
    command_tree_text = text[command_tree_start:command_tree_start + 500]
    command_lines = re.findall(r'(-\[no\]|-\w+|\[\w+\])', command_tree_text)
    return command_lines

# Function to refine parsing of the command tree
def parse_refined_command_tree(text):
    command_tree_start = text.find("CommandTree")
    command_tree_end = text.find("X\n", command_tree_start)
    if command_tree_start == -1 or command_tree_end == -1:
        return "CommandTree section not found in text."
    command_tree_text = text[command_tree_start:command_tree_end].strip()
    command_lines = re.findall(r'(-\[no\]|-\w+|\[\w+\])', command_tree_text)
    return command_lines

# Function to read PDF with font metadata (Not yet successful)
def read_pdf_with_font_metadata(pdf_path, page_num=1):
    font_metadata = []
    with open(pdf_path, 'rb') as f:
        pdf_reader = PdfReader(f)
        if page_num <= len(pdf_reader.pages):
            page = pdf_reader.pages[page_num]
            content_obj = page['/Contents'].get_object()
            content = content_obj._data.decode('latin1')
            for font_cmd, text in re.findall(r'(BT[\s\S]*?ET)', content):
                font_metadata.append((font_cmd, text))
    return font_metadata

# Define directories for unzipping files
resource_module_models_isam_dir = '/home/kuehnemund/projects/resource_module_models_isam'
ISAM_renamed_pdfs_dir = '/home/kuehnemund/projects/resource_module_models_isam/models/isam/pdfs'

# Path to the 22_-_VLANConfigurationCommands PDF
vlan_config_pdf_path = os.path.join(ISAM_renamed_pdfs_dir, '22_-_VLANConfigurationCommands.pdf')

# Extract and parse text
try:
    extended_vlan_config_text = read_pdf_with_font_metadata(vlan_config_pdf_path)
    combined_text = "".join(extended_vlan_config_text)
    parsed_refined_command_tree = parse_refined_command_tree(combined_text)
except Exception as e:
    print(e)
    parsed_refined_command_tree = str(e)

parsed_refined_command_tree
