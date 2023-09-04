import fitz  # PyMuPDF
import pandas as pd
import os

def extract_tables_using_find_tables(doc, start_page=0, end_page=None):
    end_page = end_page if end_page else len(doc)
    extracted_tables = {}

    for page_num in range(start_page, end_page):
        page = doc.load_page(page_num)
        table_finder = page.find_tables()  # New function available in PyMuPDF 1.23.0

        for i, table in enumerate(table_finder.tables):
            df = table.to_pandas()  # Convert to Pandas DataFrame
            extracted_tables[f"Page_{page_num}_Table_{i}"] = df

    return extracted_tables

# Usage example
ISAM_renamed_pdfs_dir = '/home/kuehnemund/projects/resource_module_models_isam/models/isam/pdfs'
vlan_config_pdf_path = os.path.join(ISAM_renamed_pdfs_dir, '22_-_VLANConfigurationCommands.pdf')

doc = fitz.open(vlan_config_pdf_path)

# Extract tables from all pages
extracted_tables = extract_tables_using_find_tables(doc)

# Now `extracted_tables` is a dictionary where keys are strings like "Page_0_Table_0"
# and values are Pandas DataFrames containing the table data.


def merge_split_tables(tables_dict):
    merged_tables = {}
    previous_df = None
    previous_table_key = None

    for current_table_key, current_df in sorted(tables_dict.items()):
        current_page = int(current_table_key.split("_")[1])

        # No previous table, just set the current one as previous and continue
        if previous_df is None:
            if current_df.shape[0] > 1:
                previous_df = current_df.iloc[1:].copy()
            previous_table_key = current_table_key
            continue

        # Get the previous page number
        previous_page = int(previous_table_key.split("_")[1])

        # Handle one-row tables separately
        if current_df.shape[0] <= 1:
            merged_tables[previous_table_key] = previous_df
            previous_df = None
            continue

        # Main merging logic
        cell_value = current_df.iloc[0, 0]
        if current_page == previous_page + 1 and (pd.isna(cell_value) or cell_value == '' or (isinstance(cell_value, str) and cell_value.strip().isspace())):
            print(previous_df.iloc[-1])
            print(current_df.iloc[1])
            merged_row = previous_df.iloc[-1] + current_df.iloc[1]
            previous_df.iloc[-1] = merged_row
            current_df.drop(current_df.index[1], inplace=True)
            current_df.reset_index(drop=True, inplace=True)
            previous_df = pd.concat([previous_df, current_df.iloc[1:]]).reset_index(drop=True)
            previous_table_key = f"Page_{previous_page}-{current_page}_Merged"
        else:
            merged_tables[previous_table_key] = previous_df
            previous_df = current_df.iloc[1:].copy()

        previous_table_key = current_table_key

    if previous_df is not None:
        merged_tables[previous_table_key] = previous_df

    return merged_tables


merged_tables = merge_split_tables(extracted_tables)

output_dir = '/home/kuehnemund/projects/resource_module_models_isam/test_csv'
os.makedirs(output_dir, exist_ok=True)
for table_name, df in merged_tables.items():
    output_file_path = os.path.join(output_dir, f"{table_name}.csv")
    df.to_csv(output_file_path, index=False)