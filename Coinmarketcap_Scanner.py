import json
import os
import pandas as pd
import requests
import time
from datetime import datetime
from typing import Dict, List, Any, Optional


def extract_data_from_excel(excel_file: str, sheet_name: str = "Assets missing info") -> List[Dict[str, Any]]:
    """Extract data from Excel file and create structured data"""
    try:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)

        # Map columns based on keywords
        column_mapping = {}
        keyword_maps = {
            'Blockchain': ['blockchain', 'network', 'chain', 'platform'],
            'Name': ['name', 'asset', 'currency', 'token'],
            'Symbol': ['symbol', 'ticker', 'code'],
            'Address': ['address', 'contract', 'hash'],
            'Price': ['price', 'value', 'cost', 'worth']
        }

        excel_columns = df.columns.tolist()
        # Try to find columns by keywords
        for field, keywords in keyword_maps.items():
            for col in excel_columns:
                if any(keyword in col.lower() for keyword in keywords):
                    if field == 'Name' and 'blockchain' in col.lower():
                        continue
                    column_mapping[field] = col
                    break

        # Fall back to positional mapping if needed
        field_positions = ['Blockchain', 'Name', 'Symbol', 'Address', 'Price']
        for i, field in enumerate(field_positions):
            if field not in column_mapping and i < len(excel_columns):
                column_mapping[field] = excel_columns[i]

        # Create structured data
        result = []
        for index, row in df.iterrows():
            entry = {"Row": index + 2}  # Excel rows start from 1, and we have a header

            for json_field, excel_col in column_mapping.items():
                if excel_col in row:
                    value = row[excel_col]
                    # Convert values to strings properly, handling NaN values
                    entry[json_field] = str(value) if pd.notna(value) else "Not found"

            # Initialize additional fields
            entry["MarketCap"] = "Not found"
            entry["Network"] = "Not found"

            # Ensure all basic fields exist
            for field in ['Blockchain', 'Name', 'Symbol', 'Address', 'Price']:
                if field not in entry:
                    entry[field] = "Not found"

            result.append(entry)

        # Sort by row number
        return sorted(result, key=lambda x: x["Row"])

    except Exception as e:
        return []


def enhance_with_coinmarketcap(data: List[Dict[str, Any]], api_key: str, batch_size: int = 10) -> List[Dict[str, Any]]:
    """Enhance crypto data using CoinMarketCap API - optimized version with address-first approach"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not api_key:
        return data

    # Test API key
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/map'
    headers = {'Accepts': 'application/json', 'X-CMC_PRO_API_KEY': api_key}
    try:
        response = requests.get(url, headers=headers, params={'limit': 1})
    except Exception:
        pass

    # Setup API endpoints
    api_urls = {
        'metadata': 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/info',
        'quotes': 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
    }
    headers = {'Accepts': 'application/json', 'X-CMC_PRO_API_KEY': api_key}

    # Rate limiting
    rate_limit = {'per_minute': 30, 'count': 0, 'start_time': time.time()}

    # Output collections
    enhanced_data = []
    not_found = []
    corrections = []

    # Cache for metadata to reduce API calls - store by address, symbol, and name
    metadata_cache = {
        'by_address': {},
        'by_symbol': {},
        'by_name': {}
    }

    try:
        # Sort by row number
        sorted_data = sorted(data, key=lambda x: x["Row"])
        total = len(sorted_data)
        processed = 0

        for i, entry in enumerate(sorted_data):
            address = entry.get('Address', '').strip()
            symbol = entry.get('Symbol', '').strip()
            name = entry.get('Name', '').strip()

            # Add lookup method field to track how we found this data
            entry['LookupMethod'] = 'Not found'

            print(f"Row {entry['Row']} ({i + 1}/{total}): Processing asset...")

            try:
                coin_data = None
                search_method = None

                # First try by address (most reliable)
                if address and address != "Not found":
                    if address in metadata_cache['by_address']:
                        coin_data = metadata_cache['by_address'][address]
                        search_method = 'address_cache'
                    else:
                        # In real implementation, would need to call an API that allows search by address
                        # CoinMarketCap doesn't directly support this, so we might need another API
                        # This is just a placeholder for the logic
                        pass

                # Next try by symbol
                if not coin_data and symbol and symbol != "Not found":
                    if symbol in metadata_cache['by_symbol']:
                        coin_data = metadata_cache['by_symbol'][symbol]
                        search_method = 'symbol_cache'
                    else:
                        handle_rate_limiting(rate_limit)
                        parameters = {'symbol': symbol}
                        response = make_api_request(api_urls['metadata'], headers, parameters, rate_limit)

                        if response and response.status_code == 200:
                            metadata = response.json()
                            if 'data' in metadata and symbol in metadata['data']:
                                coin_data = metadata['data'][symbol]
                                metadata_cache['by_symbol'][symbol] = coin_data
                                search_method = 'symbol_api'

                # Finally try by name
                if not coin_data and name and name != "Not found":
                    if name in metadata_cache['by_name']:
                        coin_data = metadata_cache['by_name'][name]
                        search_method = 'name_cache'
                    else:
                        # CoinMarketCap doesn't have a direct name search, but we can try a map lookup
                        # and filter results
                        handle_rate_limiting(rate_limit)
                        # This would ideally use a search endpoint, but we're approximating
                        map_params = {'limit': 5000}  # Get a large list to search
                        response = make_api_request('https://pro-api.coinmarketcap.com/v1/cryptocurrency/map',
                                                    headers, map_params, rate_limit)

                        if response and response.status_code == 200:
                            map_data = response.json()
                            if 'data' in map_data:
                                # Try to find a coin with a name that closely matches
                                found = False
                                for coin in map_data['data']:
                                    # Check for exact match or close match
                                    if coin['name'].lower() == name.lower() or name.lower() in coin['name'].lower():
                                        # Get the full metadata for this coin
                                        handle_rate_limiting(rate_limit)
                                        detail_params = {'id': coin['id']}
                                        detail_response = make_api_request(api_urls['metadata'],
                                                                           headers, detail_params, rate_limit)

                                        if detail_response and detail_response.status_code == 200:
                                            detail_data = detail_response.json()
                                            if 'data' in detail_data and str(coin['id']) in detail_data['data']:
                                                coin_data = detail_data['data'][str(coin['id'])]
                                                metadata_cache['by_name'][name] = coin_data
                                                search_method = 'name_api'
                                                found = True
                                                break

                # Process the coin data if found
                if coin_data:
                    entry['LookupMethod'] = search_method

                    # Check and correct name if needed
                    if 'name' in coin_data:
                        if entry['Name'] != "Not found" and entry['Name'] != coin_data['name']:
                            corrections.append({
                                "Row": entry['Row'],
                                "Field": "Name",
                                "Original": entry['Name'],
                                "Corrected": coin_data['name']
                            })
                        entry['Name'] = coin_data['name']

                    # Get blockchain and network details
                    if 'platform' in coin_data and coin_data['platform']:
                        entry['Blockchain'] = coin_data['platform']['name']
                        if 'symbol' in coin_data['platform']:
                            entry['Network'] = coin_data['platform']['symbol']

                    # Add metadata
                    for field, source in [('Slug', 'slug'), ('DateAdded', 'date_added')]:
                        if source in coin_data:
                            entry[field] = coin_data[source]

                    if 'tags' in coin_data and coin_data['tags']:
                        try:
                            entry['Tags'] = ','.join(coin_data['tags'])
                        except TypeError:
                            # Handle case when tags is not iterable
                            entry['Tags'] = str(coin_data['tags'])

                    # Get quotes data
                    coin_id = coin_data.get('id')
                    if coin_id:
                        quote_key = str(coin_id)
                        # Check if we already have quotes data cached
                        if 'quotes' in metadata_cache and quote_key in metadata_cache['quotes']:
                            process_quotes_data(entry, metadata_cache['quotes'][quote_key])
                        else:
                            # Make a new request for quotes
                            handle_rate_limiting(rate_limit)
                            quote_params = {'id': coin_id}
                            quote_response = make_api_request(api_urls['quotes'], headers, quote_params, rate_limit)

                            if quote_response and quote_response.status_code == 200:
                                quote_data = quote_response.json()

                                if 'data' in quote_data and quote_key in quote_data['data']:
                                    # Cache the quotes data
                                    if 'quotes' not in metadata_cache:
                                        metadata_cache['quotes'] = {}

                                    metadata_cache['quotes'][quote_key] = quote_data['data'][quote_key]
                                    process_quotes_data(entry, quote_data['data'][quote_key])
                else:
                    # Record why we couldn't find it
                    reason = "No valid identifiers found"
                    if not symbol and not name and not address:
                        reason = "No symbol, name, or address available"
                    elif not symbol and not name:
                        reason = f"Address '{address}' not found, no symbol or name available"
                    elif not symbol:
                        reason = f"Address '{address}' not found, name '{name}' not found"
                    else:
                        reason = f"Symbol '{symbol}' not found"

                    not_found.append({
                        "Row": entry['Row'],
                        "Reason": reason
                    })

                    # If we have a symbol, remember that it wasn't found to avoid future lookups
                    if symbol:
                        metadata_cache['by_symbol'][symbol] = None

            except Exception as e:
                not_found.append({
                    "Row": entry['Row'],
                    "Reason": f"Error: {str(e)}"
                })

            # Ensure no empty fields
            for field in entry:
                if not entry[field] and field != "Row":
                    entry[field] = "Not found"

            # Add to enhanced data
            enhanced_data.append(entry)
            processed += 1

            # Small delay between requests to avoid overloading the API
            time.sleep(0.25)

            # Save intermediate results (but don't prompt)
            if i > 0 and i % batch_size == 0:
                save_results_to_file(enhanced_data, timestamp, i, total, batch_size)

    except KeyboardInterrupt:
        pass

    finally:
        # Final check for empty fields
        for entry in enhanced_data:
            for field in entry:
                if not entry[field] and field != "Row":
                    entry[field] = "Not found"

        # Save all results to a single JSON file
        output_file = f'enhanced_crypto_data_{timestamp}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_data, f, indent=2, ensure_ascii=False)

        # Also save additional debug files if needed
        if not_found:
            not_found_file = f'not_found_entries_{timestamp}.json'
            with open(not_found_file, 'w', encoding='utf-8') as f:
                json.dump(not_found, f, indent=2, ensure_ascii=False)

        if corrections:
            corrections_file = f'data_corrections_{timestamp}.json'
            with open(corrections_file, 'w', encoding='utf-8') as f:
                json.dump(corrections, f, indent=2, ensure_ascii=False)

    return enhanced_data


def save_results_to_file(enhanced_data: List[Dict[str, Any]], timestamp: str,
                         current_index: int, total: int, batch_size: int) -> None:
    """Save intermediate results to file"""
    intermediate_file = f'enhanced_crypto_data_intermediate_{timestamp}.json'
    with open(intermediate_file, 'w', encoding='utf-8') as f:
        json.dump(enhanced_data, f, indent=2, ensure_ascii=False)


def handle_rate_limiting(rate_limit: Dict[str, Any]) -> None:
    """Handle API rate limiting"""
    current_time = time.time()
    if current_time - rate_limit['start_time'] > 60:
        rate_limit['count'] = 0
        rate_limit['start_time'] = current_time

    if rate_limit['count'] >= rate_limit['per_minute']:
        wait_time = 60 - (current_time - rate_limit['start_time'])
        if wait_time > 0:
            time.sleep(wait_time)
            rate_limit['count'] = 0
            rate_limit['start_time'] = time.time()


def make_api_request(url: str, headers: Dict[str, str], params: Dict[str, Any],
                     rate_limit: Dict[str, Any]) -> Optional[requests.Response]:
    """Make an API request with rate limiting and error handling"""
    try:
        response = requests.get(url, headers=headers, params=params)
        rate_limit['count'] += 1

        # Handle 429 rate limit
        if response.status_code == 429:
            time.sleep(60)
            response = requests.get(url, headers=headers, params=params)
            rate_limit['count'] = 1
            rate_limit['start_time'] = time.time()

        return response
    except Exception as e:
        return None


def process_quotes_data(entry: Dict[str, Any], crypto_data: Dict[str, Any]) -> None:
    """Process and extract quotes data into entry"""
    # Update price if needed
    if entry['Price'] == "Not found" and 'quote' in crypto_data and 'USD' in crypto_data['quote']:
        entry['Price'] = str(crypto_data['quote']['USD']['price'])

    # Add market cap and metrics
    if 'quote' in crypto_data and 'USD' in crypto_data['quote']:
        usd = crypto_data['quote']['USD']

        # Market cap
        if 'market_cap' in usd and usd['market_cap']:
            entry['MarketCap'] = str(usd['market_cap'])

        # Other metrics
        for field, data_field in [
            ('Volume24h', 'volume_24h'),
            ('PercentChange24h', 'percent_change_24h'),
            ('PercentChange7d', 'percent_change_7d'),
            ('PercentChange30d', 'percent_change_30d')
        ]:
            entry[field] = str(usd[data_field]) if data_field in usd and usd[data_field] else "Not found"

    # Supply info
    for field, data_field in [
        ('CirculatingSupply', 'circulating_supply'),
        ('MaxSupply', 'max_supply')
    ]:
        entry[field] = str(crypto_data[data_field]) if data_field in crypto_data and crypto_data[
            data_field] else "Not found"


def merge_with_existing_data(current_data: List[Dict[str, Any]], existing_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge data from existing JSON with current data"""
    # Create lookup dictionaries for faster access
    existing_by_symbol = {}
    existing_by_address = {}
    existing_by_name = {}

    # Build lookup tables from existing data
    for item in existing_data:
        symbol = item.get('Symbol', '').strip
    
    # Note: This function appears to be incomplete in the original code
    return current_data


def process_crypto_data(excel_file: str, api_key: str, existing_json_file: str = None, batch_size: int = 10) -> List[Dict[str, Any]]:
    """Main function to process crypto data from Excel and enhance it with API data"""
    if not os.path.exists(excel_file):
        return []

    # Extract data from Excel
    extracted_data = extract_data_from_excel(excel_file)
    if not extracted_data:
        return []

    # Check if we want to use existing JSON data as a source
    existing_data = []
    if existing_json_file and os.path.exists(existing_json_file):
        try:
            with open(existing_json_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)

            # Merge existing data with extracted data where appropriate
            extracted_data = merge_with_existing_data(extracted_data, existing_data)
        except Exception:
            pass

    # Enhance data with CoinMarketCap API
    result = enhance_with_coinmarketcap(extracted_data, api_key, batch_size)

    # Save a final single JSON file with all the data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_file = f'crypto_data_final_{timestamp}.json'
    with open(final_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return result


# For backward compatibility if the script is run directly
def coinmarketcap_scan():

    # Get user inputs
    excel_file = input("Enter path to Excel file [default: Fireblocks_Task__-_assets_with_missing_info.xlsx]: ").strip() or "Fireblocks_Task__-_assets_with_missing_info.xlsx"
    
    api_key = input("Enter your CoinMarketCap API key: ").strip()
    
    use_existing_data = input("Do you want to use existing JSON data to supplement lookups? (y/n) [default: n]: ").strip().lower() == 'y'
    
    existing_json_file = None
    if use_existing_data:
        existing_json_file = input("Enter path to existing JSON data file: ").strip()
    
    try:
        batch_size_input = input("Enter batch size for intermediate saves [default: 10]: ").strip()
        batch_size = int(batch_size_input) if batch_size_input else 10
    except ValueError:
        batch_size = 10
    
    result = process_crypto_data(excel_file, api_key, existing_json_file, batch_size)
    
    print("===== Process completed =====")

if __name__ == "__main__":
    coinmarketcap_scan()