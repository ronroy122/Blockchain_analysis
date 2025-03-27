import requests
import time
import pandas as pd
import os
import random
import json
from bs4 import BeautifulSoup

# Constants
DELAY_BETWEEN_CALLS = 2  # seconds between network requests
MAX_RETRIES = 3


def is_valid_price(price_str):
    """Validates if a string contains a price."""
    if not price_str:
        return False
    has_digit = any(char.isdigit() for char in price_str)
    price_indicators = ['$', '€', '£', 'usd', 'eur', 'gbp']
    has_currency = any(indicator in price_str.lower() for indicator in price_indicators)
    return has_digit or has_currency


def parse_name_price(text):
    """Splits text by '|' separator and identifies name vs price."""
    if '|' not in text:
        return text, ""

    parts = text.split('|')
    part1 = parts[0].strip()
    part2 = parts[1].strip() if len(parts) > 1 else ""

    # Determine which part is the price
    if is_valid_price(part1) and not is_valid_price(part2):
        return part2, part1
    elif is_valid_price(part2) and not is_valid_price(part1):
        return part1, part2
    else:
        return part1, part2


def get_token_symbol_from_blockchain_explorer(contract_address, network):
    """Scrapes blockchain explorer to extract token data."""
    if network == 'Ethereum':
        base_url = f"https://etherscan.io/token/{contract_address}"
    elif network == 'BNB Smart Chain':
        base_url = f"https://bscscan.com/token/{contract_address}"
    else:
        return "", "", ""

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(base_url, headers=headers)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Method 1: Look for the main h1 title
                h1_element = soup.find('h1', class_='mb-1')
                if h1_element:
                    title_text = h1_element.text.strip()
                    if '(' in title_text and ')' in title_text:
                        full_name = title_text.split('(')[0].strip()
                        symbol = title_text.split('(')[1].split(')')[0].strip()
                        name, price = parse_name_price(full_name)
                        return symbol, name, price

                # Method 2: Search in token profile area
                profile_boxes = soup.find_all('div', class_='col-md-8')
                token_name = ""
                token_symbol = ""
                token_price = ""

                for box in profile_boxes:
                    labels = box.find_all('div', class_='col-md-4')
                    values = box.find_all('div', class_='col-md-8')

                    for i, label in enumerate(labels):
                        if i < len(values):
                            label_text = label.text.strip()
                            value_text = values[i].text.strip()

                            if "Symbol" in label_text:
                                token_symbol = value_text
                            if "Name" in label_text:
                                token_name, token_price = parse_name_price(value_text)

                if token_symbol:
                    return token_symbol, token_name, token_price

                # Method 3: Search page title
                title_element = soup.find('title')
                if title_element:
                    title_text = title_element.text.strip()
                    if " Token Tracker" in title_text:
                        name_part = title_text.split(" Token Tracker")[0].strip()
                        if '(' in name_part and ')' in name_part:
                            full_name = name_part.split('(')[0].strip()
                            symbol = name_part.split('(')[1].split(')')[0].strip()
                            name, price = parse_name_price(full_name)
                            return symbol, name, price

                # Method 4: Search within HTML
                html_text = response.text
                symbol_matches = []
                name_matches = []
                html_price = ""

                # Search for symbol in HTML
                if "symbol:" in html_text.lower():
                    parts = html_text.lower().split("symbol:")
                    if len(parts) > 1:
                        potential_symbols = parts[1].split(',')[0]
                        clean_symbol = ''.join([c for c in potential_symbols if c.isalnum()])[:10]
                        if clean_symbol:
                            symbol_matches.append(clean_symbol.upper())

                # Search for name in HTML
                html_name = ""
                if "name:" in html_text.lower():
                    parts = html_text.lower().split("name:")
                    if len(parts) > 1:
                        potential_name = parts[1]
                        for delimiter in ['"', "'"]:
                            if delimiter in potential_name:
                                name_part = potential_name.split(delimiter)
                                if len(name_part) > 1:
                                    html_name = name_part[1]
                                    html_name, html_price = parse_name_price(html_name)
                                    break

                        if html_name:
                            name_matches.append(html_name)

                if symbol_matches:
                    symbol = symbol_matches[0]
                    name = name_matches[0] if name_matches else ""
                    return symbol, name, html_price

                return "", "", ""

            elif response.status_code == 429:  # Rate limit
                wait_time = (attempt + 1) * 5 + random.uniform(1, 5)
                time.sleep(wait_time)
            else:
                break

        except Exception:
            time.sleep(DELAY_BETWEEN_CALLS)

    return "", "", ""


def extract_tokens_from_excel(file_path):
    """Filters Excel data for tokens with addresses but missing symbols."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        df = pd.read_excel(file_path, header=None)
        filtered_df = df[((df[0] == 'Ethereum') | (df[0] == 'BNB Smart Chain')) & (df[3].notna())].copy()
        filtered_df['excel_row'] = filtered_df.index + 1

        result = []
        for _, row in filtered_df.iterrows():
            network = row[0]
            existing_symbol = row[2] if pd.notna(row[2]) else ""
            contract_address = row[3]
            excel_row = int(row['excel_row'])

            # Add to list only rows without existing symbol
            if not existing_symbol:
                result.append([excel_row, network, existing_symbol, contract_address])

        return result
    except Exception as e:
        raise e


def parse_row_selection(selection, max_row):
    """Converts a string like "1,3-5,8" into a list of row numbers."""
    selected_rows = set()

    if not selection or selection.strip() == "":
        return list(range(1, max_row + 1))

    for part in selection.split(','):
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                start = max(1, start)
                end = min(end, max_row)
                selected_rows.update(range(start, end + 1))
            except ValueError:
                pass
        else:
            try:
                row_num = int(part)
                if 1 <= row_num <= max_row:
                    selected_rows.add(row_num)
            except ValueError:
                pass

    return sorted(list(selected_rows))


def get_symbols_for_tokens(input_file, row_selection=None):
    """Processes Excel rows to retrieve token information."""
    all_token_rows = extract_tokens_from_excel(input_file)
    if not all_token_rows:
        return []

    max_row = max(row[0] for row in all_token_rows)

    # Process row selection
    if row_selection is not None:
        selected_row_numbers = parse_row_selection(row_selection, max_row)
        token_rows = [row for row in all_token_rows if row[0] in selected_row_numbers]
    else:
        token_rows = all_token_rows

    tokens_info_list = []
    total_rows = len(token_rows)

    # Process each row
    for idx, row_data in enumerate(token_rows):
        row_num, network, _, contract_address = row_data
        # Print progress update
        print(f"Row {row_num} ({idx+1}/{total_rows}): Processing asset...")
        
        symbol, name, price = get_token_symbol_from_blockchain_explorer(contract_address, network)

        result = {
            "Row": row_num,
            "Name": name,
            "Symbol": symbol if symbol else "Not found",
            "Blockchain": network,
            "Address": contract_address,
            "Price": price if price and is_valid_price(price) else "Not available"
        }

        if not symbol:
            result["Reason"] = "Symbol not found"

        if price and not is_valid_price(price):
            # If price doesn't look valid, it might be part of the name
            result["Name"] = f"{result['Name']} {price}".strip()
            result["Price"] = "Not available"

        tokens_info_list.append(result)
        time.sleep(DELAY_BETWEEN_CALLS)

    return tokens_info_list


def etherscan_bnb():
    """Main function that processes tokens and saves results."""
    print("=== Blockchain Token Symbol and Name Extractor ===")

    input_file = "Fireblocks_Task__-_assets_with_missing_info.xlsx"

    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        exit(1)

    all_rows = extract_tokens_from_excel(input_file)
    if not all_rows:
        print("No Ethereum/BNB Smart Chain tokens with addresses found in the Excel file.")
        exit(0)

    print(f"Found {len(all_rows)} Ethereum/BNB Smart Chain tokens with addresses and missing symbols.")
    
    # Process all rows without asking user
    row_selection = None

    start_time = time.time()
    tokens_info = get_symbols_for_tokens(input_file, row_selection=row_selection)

    print(f"\nEstimated runtime: {time.time() - start_time:.2f} seconds")
    print(f"Found info for {len(tokens_info)} tokens")

    # Save results to JSON
    if tokens_info:
        results_file = "token_info_results.json"
        try:
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(tokens_info, f, indent=2, ensure_ascii=False)
            print(f"Results saved to {results_file}")
        except Exception as e:
            print(f"Error saving results: {str(e)}")


# Main execution
if __name__ == "__main__":
    etherscan_bnb()
