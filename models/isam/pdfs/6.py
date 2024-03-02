def extract_table_data(parsed_data, table_start_keyword, table_end_keyword):
    table_data = defaultdict(list)
    capture = False
    row_num = 0
    
    for entry in parsed_data:
        text = entry["text"].strip()
        pos_y = entry["position"][1]
        
        if table_start_keyword in text:
            capture = True
            continue  # Skip the title line
        
        if capture:
            if table_end_keyword and table_end_keyword in text:
                break
            
            # Update row number if y-coordinate changes significantly
            if table_data and abs(list(table_data.keys())[-1] - pos_y) > 5:
                row_num += 1
            
            table_data[row_num].append({
                'text': text,
                'x_start': entry["position"][0],
                'x_end': entry["position"][2]
            })
    
    # Sort data in each row by x-coordinate
    for row in table_data.values():
        row.sort(key=lambda x: x['x_start'])
    
    # Convert to list of lists for easier manipulation
    sorted_table_data = [table_data[k] for k in sorted(table_data.keys())]
    
    return sorted_table_data

def extract_table_data_improved(parsed_data, table_header_keywords):
    """
    Improved function to extract table data based on user's more detailed PDF structure.
    """
    table_data = defaultdict(lambda: defaultdict(list))
    capture = False
    column_boundaries = {}
    
    for entry in parsed_data:
        text = entry["text"].strip()
        pos_x_start = entry["position"][0]
        pos_y = entry["position"][1]
        
        # Check if we've reached a new table
        if any(keyword in text for keyword in table_header_keywords):
            capture = True
            column_boundaries = {}  # Reset column boundaries for new table
            continue  # Skip the title line

        # Check for table headers to set column boundaries
        for keyword in table_header_keywords:
            if keyword in text:
                column_boundaries[keyword] = pos_x_start

        if capture:
            # Determine which column this entry belongs to
            for i, keyword in enumerate(table_header_keywords):
                next_keyword = table_header_keywords[i + 1] if i + 1 < len(table_header_keywords) else None
                
                if next_keyword:
                    if column_boundaries[keyword] <= pos_x_start < column_boundaries[next_keyword]:
                        column = keyword
                        break
                else:
                    if pos_x_start >= column_boundaries[keyword]:
                        column = keyword
                        break
            
            table_data[pos_y][column].append(text)

    # Sort table by y-coordinate for rows
    sorted_table_data = {k: table_data[k] for k in sorted(table_data.keys())}
    
    return sorted_table_data