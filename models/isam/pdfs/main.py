import fitz  # PyMuPDF
import pandas as pd
import os
import json
import re
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from collections import deque




def gen_dict_extract(key, var):
    if hasattr(var,'items'): # hasattr(var,'items') for python 3
        for k, v in var.items(): # var.items() for python 3
            if k == key:
                yield v
            if isinstance(v, dict):
                for result in gen_dict_extract(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in gen_dict_extract(key, d):
                        yield result

def is_header(entry, y_threshold=40):
    return entry["position"][1] <= y_threshold

def is_footer(entry, y_threshold=700):
    return entry["position"][1] >= y_threshold

def remove_headers_and_footers(data):
    with ThreadPoolExecutor() as executor:
        header_flags = list(executor.map(is_header, data))
        footer_flags = list(executor.map(is_footer, data))
    
    return [entry for entry, h_flag, f_flag in zip(data, header_flags, footer_flags) if not h_flag and not f_flag]

def flags_decomposer(flags):
    l = []
    if flags & 2 ** 0:
        l.append("superscript")
    if flags & 2 ** 1:
        l.append("italic")
    if flags & 2 ** 2:
        l.append("serifed")
    else:
        l.append("sans")
    if flags & 2 ** 3:
        l.append("monospaced")
    else:
        l.append("proportional")
    if flags & 2 ** 4:
        l.append("bold")
    return ", ".join(l)

def extract_command_tree(data, output_file):
    
    # Remove headers and footers in parallel
    data = remove_headers_and_footers(data)
    
    command_tree = []
    capture = False
    
    for entry in data:
        if entry["text"].strip() == "CommandTree":
            capture = True
            command_tree.append(entry)
            continue
        
        if capture:
            if entry["text"].strip().startswith(("-", "X")):
                command_tree.append(entry)
            else:
                break  # Stop capturing when a line not starting with "-" is encountered
    
    with open(output_file, 'w') as f:
        json.dump(command_tree, f, indent=4)
    
    return command_tree

def extract_text_with_details(pdf_path, output_file):
    output_data = []
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        blocks = page.get_text("dict", flags=11)["blocks"]
        for block in blocks:
            for line in block["lines"]:
                line_data = {"text": "", "font_details": [], "position": line["bbox"]}
                line_data["page"] = page_num
                for span in line["spans"]:
                    line_data["text"] += span["text"] + " "
                    font_properties = {
                        "font": span["font"],
                        "flags": flags_decomposer(span["flags"]),
                        "size": span["size"],
                        "color": f"#{span['color']:06x}"
                    }
                    line_data["font_details"].append(font_properties)
                output_data.append(line_data)

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=4)
    
    return output_data

def create_ansible_argument_spec(command_tree_data):
    argument_spec = {}
    stack = []
    
    for entry in command_tree_data:
        text = entry['text'].strip()
        position = entry['position'][0]
        
        while stack and stack[-1]['position'][0] >= position:
            stack.pop()
        
        parent = stack[-1]['spec'] if stack else argument_spec
        
        arg_type = 'str'  # Default type
        argument_entry = {}
        
        if text.startswith("-"):
            command_name = text[1:].strip()
            suboptions = None
            
            # Handle "[no]" for both regular and "----" starting texts
            if "[no]" in text:
                arg_type = 'bool'
                command_name = command_name.replace("[no]", "").strip()
                
            if text.startswith("----"):
                command_name = text[4:].strip()
                suboptions = {}
                argument_entry[command_name] = {
                    'type': 'dict',
                    'options': suboptions
                }
            else:
                argument_entry[command_name] = {
                    'type': arg_type,
                    'description': [],
                    'required': False
                }
            
            parent.update(argument_entry)
            if suboptions is not None:
                stack.append({'position': entry['position'], 'spec': suboptions})
    
    return argument_spec

def find_command_start_page_regex(pdf_doc, command_name, start_page=4):
    """Find the start page of a command's details in a PDF document using regex to match individual terms."""
    # Remove optional parts and split the command into individual terms
    simplified_command_name = re.sub(r"\[.*?\]", "", command_name)
    terms = simplified_command_name.split()
    
    # Prepare a regex pattern to match individual terms with any characters in between
    pattern = re.compile(r".*".join(map(re.escape, terms)), re.I)
    
    for page_num in range(start_page, len(pdf_doc)):
        page_text = pdf_doc.load_page(page_num).get_text()
        if pattern.search(page_text):
            return page_num
    return None

# Function to find the subchapter number based on the text size
def find_subchapter_numbers(parsed_data, text_size=20.0):
    subchapter_numbers = []
    subchapter_numbers_with_pages = []
    for entry in parsed_data:
        if any(font_detail['size'] == text_size for font_detail in entry['font_details']):
            # Extract the subchapter number from the text
            match = re.search(r'\d+(\.\d+)+', entry['text'])
            if match:
                subchapter_numbers.append(match.group())
                subchapter_numbers_with_pages.append((match.group(), entry['page']))
    return subchapter_numbers, subchapter_numbers_with_pages

def match_commands_to_subchapters(parsed_data, subchapters_with_pages):
    matched_commands = {}
    last_trigger = None

    for entry in parsed_data:
        if "Thecommandhasthefollowingsyntax" in entry['text']:
            last_trigger = entry['page']
        elif last_trigger is not None:
            closest_subchapter = min(subchapters_with_pages, key=lambda x: abs(x[1] - last_trigger))
            if closest_subchapter not in matched_commands:
                matched_commands[closest_subchapter] = []
            matched_commands[closest_subchapter].append(entry['text'])
            last_trigger = None

    return matched_commands

# Function to isolate data for each subchapter based on the subchapter number and page number
def isolate_subchapter_data(parsed_data, subchapter_numbers):
    subchapter_data = {num: [] for num in subchapter_numbers}
    current_subchapter = None
    
    for entry in parsed_data:
        # Check if the entry text contains a subchapter number
        for num in subchapter_numbers:
            if num in entry["text"]:
                current_subchapter = num
                break
        
        # Add the entry to the appropriate subchapter
        if current_subchapter:
            entry_with_subchapter = entry.copy()
            entry_with_subchapter["subchapter"] = current_subchapter
            subchapter_data[current_subchapter].append(entry_with_subchapter)
    
    return subchapter_data

def extract_table_info(json_entries):
    table_info = []
    for entry in json_entries:
        # Regex pattern to find table number
        pattern = r'Table(\d+\.\d+-\d+)'
        match = re.search(pattern, entry["text"])
        if match:
            table_number = match.group(1)
            page_number = entry["page"]
            table_info.append((table_number, page_number))
    return table_info

def extract_tables_using_find_tables(doc, start_page=0, end_page=None):
    end_page = end_page if end_page else len(doc)
    extracted_tables = []

    for page_num in range(start_page, end_page):
        page = doc.load_page(page_num)
        table_finder = page.find_tables()  # New function available in PyMuPDF 1.23.0

        for i, table in enumerate(table_finder.tables):
            df = table.to_pandas()  # Convert to Pandas DataFrame
            extracted_tables.append((page_num, df))

    return extracted_tables

def merge_tables_based_on_info(extracted_tables, table_info):
    merged_tables = {}
    table_queue = deque()
    merged_df = None
    current_table_info = None  # Initialize variable to keep track of the current table info

    for page_num, df in extracted_tables:
        # Check if there's new table info for this page and add it to the queue
        if not table_queue:  # Only if table_queue is empty
            new_table_info = [(number, page) for number, page in table_info if page == page_num]
            table_queue.extend(new_table_info)

        # If queue is not empty, we have a new table
        if table_queue:
            # Save the previous table before starting a new one, if any
            if merged_df is not None and current_table_info is not None:
                merged_tables[current_table_info] = merged_df

            # Start a new table
            current_table_info, _ = table_queue.popleft()  # Get the table number
            merged_df = df
        else:
            # This is a continuation of the last table
            # Check if the first cell is empty
            cell_value = df.iloc[0, 0]
            is_empty_cell = pd.isna(cell_value) or cell_value == '' or (isinstance(cell_value, str) and cell_value.strip().isspace())

            if is_empty_cell:
                # Merge the last row of the previous table with the first row of the current table
                merged_row = merged_df.iloc[-1] + df.iloc[0]
                merged_df.iloc[-1] = merged_row

                # Drop the merged row from the current table
                df.drop(df.index[0], inplace=True)
                df.reset_index(drop=True, inplace=True)

            # Concatenate the remaining part of the current table to the previous table
            merged_df = pd.concat([merged_df, df]).reset_index(drop=True)

    # Save the last table, if any
    if merged_df is not None and current_table_info is not None:
        merged_tables[current_table_info] = merged_df

    return merged_tables


def merge_split_tables_v2(tables_dict):
    merged_tables = {}
    previous_df = None
    first_table_key = None

    # Sort tables based on the numeric part of their keys
    sorted_tables_dict = sorted(tables_dict.items(), key=lambda x: int(re.search(r'\d+', x[0]).group()))

    for current_table_key, current_df in sorted_tables_dict:
        current_page = int(current_table_key.split("_")[1])

        if previous_df is None:
            previous_df = current_df.copy()
            first_table_key = current_table_key
            previous_page = int(current_table_key.split("_")[1])
            continue

        # Check if the tables are on consecutive pages and the first cell is empty
        cell_value = current_df.iloc[0, 0]
        is_empty_cell = pd.isna(cell_value) or cell_value == '' or (isinstance(cell_value, str) and cell_value.strip().isspace())

        if current_page == previous_page + 1 and is_empty_cell:
            # Merge the last row of the previous table with the second row of the current table
            merged_row = previous_df.iloc[-1] + current_df.iloc[0]
            previous_df.iloc[-1] = merged_row

            # Drop the merged row from the current table
            current_df.drop(current_df.index[0], inplace=True)
            current_df.reset_index(drop=True, inplace=True)

            # Concatenate the remaining part of the current table to the previous table
            previous_df = pd.concat([previous_df, current_df.iloc[1:]]).reset_index(drop=True)
        else:
            # The tables are not on consecutive pages or the first cell is not empty.
            # Save the previous table and reset the variables.
            merged_tables[first_table_key] = previous_df
            previous_df = current_df.copy()
            first_table_key = current_table_key
        previous_page = int(current_table_key.split("_")[1])

    # Save any remaining table
    if previous_df is not None:
        merged_tables[first_table_key] = previous_df

    return merged_tables

resource_module_models_isam_dir = '/home/kuehnemund/projects/resource_module_models_isam'
ISAM_renamed_pdfs_dir = '/home/kuehnemund/projects/resource_module_models_isam/models/isam/pdfs'

resource_identifier_table_header_keywords = ["ResourceIdentifier", "Type", "Description"]
command_parameter_table_header_keywords = ["Parameter", "Type", "Description"]

# Usage
vlan_config_pdf_path = os.path.join(ISAM_renamed_pdfs_dir, '22_-_VLANConfigurationCommands.pdf')
vlan_config_txt_path = os.path.join(ISAM_renamed_pdfs_dir, '22_-_VLANConfigurationCommands.json')
vlan_command_tree_txt_path = os.path.join(ISAM_renamed_pdfs_dir, '22_-_VLANCommandTree.json')
vlan_command_tree_json_path = os.path.join(ISAM_renamed_pdfs_dir, '22_-_VLANCommandTree_AnsibleSpec.json')

json_data = extract_text_with_details(vlan_config_pdf_path, vlan_config_txt_path)
cleaned_json_data = remove_headers_and_footers(json_data)

# Write cleaned json data to cleaned_data.json
with open(os.path.join(ISAM_renamed_pdfs_dir, '22_-_VLANConfigurationCommands_cleaned.json'), 'w') as f:
    json.dump(cleaned_json_data, f, indent=4)

command_tree_data = extract_command_tree(cleaned_json_data, vlan_command_tree_txt_path)
ansible_spec = create_ansible_argument_spec(command_tree_data)

subchapter, subchapters_with_pages = find_subchapter_numbers(cleaned_json_data)
subchapter_data = isolate_subchapter_data(cleaned_json_data, subchapter)

matched_commands = match_commands_to_subchapters(cleaned_json_data, subchapters_with_pages)


doc = fitz.open(vlan_config_pdf_path)
extracted_tables = extract_tables_using_find_tables(doc)
table_info = extract_table_info(cleaned_json_data)
merged_tables = merge_tables_based_on_info(extracted_tables, table_info)

with open(vlan_command_tree_json_path, 'w') as f:
    json.dump(ansible_spec, f, indent=4)