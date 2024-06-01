import fitz  # PyMuPDF
import os

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

def extract_text_with_details(pdf_path, output_file):
    with open(output_file, 'w') as f:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            blocks = page.get_text("dict", flags=11)["blocks"]
            for block in blocks:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"]
                        font_properties = f"(Font: '{span['font']}', Flags: {flags_decomposer(span['flags'])}, Size: {span['size']}, Color: #{span['color']:06x})"
                        indent = len(text) - len(text.lstrip())
                        f.write(f"{' ' * indent}{text} {font_properties}\n")


resource_module_models_isam_dir = '/home/kuehnemund/projects/resource_module_models_isam'
ISAM_renamed_pdfs_dir = '/home/kuehnemund/projects/resource_module_models_isam/models/isam/pdfs'

# Usage
vlan_config_pdf_path = os.path.join(ISAM_renamed_pdfs_dir, '22_-_VLANConfigurationCommands.pdf')
vlan_config_txt_path = os.path.join(ISAM_renamed_pdfs_dir, '22_-_VLANConfigurationCommands.txt')

extract_text_with_details(vlan_config_pdf_path, vlan_config_txt_path)
