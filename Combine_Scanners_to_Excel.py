import json
import os
import pandas as pd
from datetime import datetime
from Coingecko_Scanner import coingecko
from Eth_Bnb_Scanner import etherscan_bnb
from Coinmarketcap_Scanner import process_crypto_data


def merge_json_data(json_files, priority_order=None):
    """
    Merge data from multiple JSON files with priority handling
    
    Parameters:
        json_files (list): List of JSON file paths
        priority_order (list): List of file prefixes in order of priority (highest first)
        
    Returns:
        list: Merged data with priority handling
    """
    if priority_order is None:
        # Default priority: Etherscan/BSCScan > CoinGecko
        priority_order = ["token_info", "missing_symbols"]
        
    # Create a map of priority values (lower number = higher priority)
    priority_map = {prefix: i for i, prefix in enumerate(priority_order)}
    
    # Read all JSON files
    all_data = []
    for json_file in json_files:
        if not os.path.exists(json_file):
            print(f"Warning: JSON file not found: {json_file}")
            continue
            
        try:
            # Determine source priority based on filename
            source_priority = 999  # Default low priority
            for prefix in priority_map:
                if prefix in json_file:
                    source_priority = priority_map[prefix]
                    break
                    
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Tag each record with its source and priority
            for record in data:
                record['_source_file'] = json_file
                record['_priority'] = source_priority
                
            all_data.extend(data)
            print(f"Loaded {len(data)} records from {json_file}")
        except Exception as e:
            print(f"Error reading JSON file {json_file}: {str(e)}")
    
    # Group by row number
    row_data = {}
    for record in all_data:
        row_num = record.get('Row')
        if row_num is None:
            continue
            
        # Initialize this row if not already present
        if row_num not in row_data:
            row_data[row_num] = {}
            
        # Get priority of this record
        priority = record.get('_priority', 999)
        
        # Update fields based on priority
        for field, value in record.items():
            # Skip metadata fields
            if field.startswith('_'):
                continue
                
            # If field doesn't exist yet, or this record has higher priority, update it
            current_priority = row_data[row_num].get(f"_{field}_priority", 1000)
            if field not in row_data[row_num] or priority < current_priority:
                row_data[row_num][field] = value
                row_data[row_num][f"_{field}_priority"] = priority
    
    # Convert back to list format
    merged_data = []
    for row_num, data in row_data.items():
        # Remove priority metadata
        clean_data = {k: v for k, v in data.items() if not k.startswith('_')}
        merged_data.append(clean_data)
    
    # Sort by row number
    merged_data.sort(key=lambda x: x.get('Row', 0))
    
    return merged_data


def create_intermediate_excel(excel_file, merged_data, output_file=None):
    """
    Create an intermediate updated Excel file from merged JSON data
    
    Parameters:
        excel_file (str): Path to the original Excel file
        merged_data (list): List of merged data records
        output_file (str, optional): Path to save the updated Excel file
        
    Returns:
        str: Path to the updated Excel file
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"intermediate_crypto_data_{timestamp}.xlsx"
    
    try:
        # Read the original Excel file
        excel_data = pd.read_excel(excel_file, sheet_name="Assets missing info")
        print(f"Read Excel file with {len(excel_data)} rows")
        
        # Create dictionary to map row numbers to DataFrame indices
        row_to_index = {row + 2: row for row in range(len(excel_data))}
        
        # Get column names
        columns = excel_data.columns.tolist()
        
        # Determine column mapping based on Excel column names
        column_mapping = {}
        # Common field names to look for in column headers
        field_keywords = {
            'Blockchain': ['blockchain', 'network', 'chain', 'platform'],
            'Name': ['name', 'asset', 'currency', 'token'],
            'Symbol': ['symbol', 'ticker', 'code'],
            'Address': ['address', 'contract', 'hash'],
            'Price': ['price', 'value', 'cost', 'worth']
        }
        
        # Try to find matching columns
        for field, keywords in field_keywords.items():
            for i, col in enumerate(columns):
                if any(keyword in col.lower() for keyword in keywords):
                    # Special case to avoid matching blockchain with name
                    if field == 'Name' and any(keyword in col.lower() for keyword in field_keywords['Blockchain']):
                        continue
                    column_mapping[field] = col
                    break
        
        # Fall back to positional mapping if needed
        field_positions = ['Blockchain', 'Name', 'Symbol', 'Address', 'Price']
        for i, field in enumerate(field_positions):
            if field not in column_mapping and i < len(columns):
                column_mapping[field] = columns[i]
        
        print(f"Column mapping: {column_mapping}")
        
        # Update Excel with merged data
        update_count = 0
        for item in merged_data:
            row_num = item.get('Row')
            if row_num not in row_to_index:
                print(f"Warning: Row {row_num} not found in Excel")
                continue
                
            index = row_to_index[row_num]
            
            # Update each mapped field
            for field, col in column_mapping.items():
                if field in item and item[field] not in ["Not found", "Error", "Not available", ""]:
                    # Only update if cell is empty or value is more reliable
                    current_value = excel_data.at[index, col]
                    if pd.isna(current_value) or str(current_value).strip() == "":
                        excel_data.at[index, col] = item[field]
                        update_count += 1
        
        # Save updated Excel
        excel_data.to_excel(output_file, sheet_name="Assets missing info", index=False)
        print(f"Updated {update_count} cells in Excel file")
        print(f"Saved intermediate Excel to {output_file}")
        
        return output_file
        
    except Exception as e:
        print(f"Error creating intermediate Excel: {str(e)}")
        return excel_file  # Return original file path on error


def save_merged_to_json(merged_data, output_file=None):
    """
    Save merged data to a JSON file
    
    Parameters:
        merged_data (list): List of merged data records
        output_file (str, optional): Path to save the JSON file
        
    Returns:
        str: Path to the saved JSON file
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"merged_crypto_data_{timestamp}.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)
        print(f"Saved merged data to {output_file}")
        return output_file
    except Exception as e:
        print(f"Error saving merged data: {str(e)}")
        return None


def combined_crypto_workflow():
    """
    Main function to execute the complete crypto data workflow
    """
    print("===== Comprehensive Crypto Data Integration Workflow =====")
    
    # Step 1: Define input files
    excel_file = "Fireblocks_Task__-_assets_with_missing_info.xlsx"
    
    if not os.path.exists(excel_file):
        print(f"Error: Excel file not found: {excel_file}")
        return
    
    # Step 2: Ask if user wants to run data collection
    run_collection = input("Do you want to run data collection from CoinGecko and Blockchain Explorers? (y/n) [default: y]: ").strip().lower()
    run_collection = run_collection in ["", "y", "yes", "1"]
    
    json_files = []
    
    # Step 3: Run CoinGecko collection if requested
    if run_collection:
        print("\nRunning CoinGecko data collection...")
        try:
            coingecko()
            json_files.append("missing_symbols_results.json")
        except Exception as e:
            print(f"Error running CoinGecko collection: {str(e)}")
    else:
        if os.path.exists("missing_symbols_results.json"):
            json_files.append("missing_symbols_results.json")
    
    # Step 4: Run Etherscan/BSCScan collection if requested
    if run_collection:
        print("\nRunning Blockchain Explorer data collection...")
        try:
            etherscan_bnb()
            json_files.append("token_info_results.json")
        except Exception as e:
            print(f"Error running Blockchain Explorer collection: {str(e)}")
    else:
        if os.path.exists("token_info_results.json"):
            json_files.append("token_info_results.json")
    
    # Check if we have any JSON files
    if not json_files:
        print("No JSON files found. Please run data collection first.")
        return
    
    # Step 5: Merge JSON data with priority
    print("\nMerging data from JSON files with Etherscan/BSCScan priority...")
    merged_data = merge_json_data(json_files, ["token_info", "missing_symbols"])
    
    # Save merged data (optional, for debugging)
    merged_json = save_merged_to_json(merged_data)
    
    # Step 6: Create intermediate Excel with merged data
    print("\nCreating intermediate Excel file...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    intermediate_excel = create_intermediate_excel(
        excel_file, 
        merged_data, 
        f"intermediate_crypto_data_{timestamp}.xlsx"
    )
    
    # Step 7: Ask for CoinMarketCap API key
    print("\nNow processing with CoinMarketCap (most comprehensive data)...")
    api_key = input("Enter your CoinMarketCap API key: ").strip()
    
    if not api_key:
        print("API key is required for CoinMarketCap integration.")
        return
    
    # Step 8: Process with CoinMarketCap
    try:
        batch_size = 10  # Default batch size
        final_data = process_crypto_data(intermediate_excel, api_key, merged_json, batch_size)
        
        # Final timestamp for output files
        final_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Find the most recent final JSON file from CoinMarketCap process
        # (it creates files with timestamp in name)
        cmk_json_files = [f for f in os.listdir() if f.startswith("crypto_data_final_")]
        if cmk_json_files:
            latest_cmk_file = max(cmk_json_files, key=os.path.getctime)
            print(f"\nFound final CoinMarketCap data file: {latest_cmk_file}")
        
        # Step 9: Create final Excel with all data
        print("\nCreating final Excel file with all collected data...")
        
        # Read the original Excel to preserve structure
        original_df = pd.read_excel(excel_file, sheet_name="Assets missing info")
        
        # Load the final JSON data from CoinMarketCap
        final_json_path = f"crypto_data_final_{final_timestamp}.json"
        if os.path.exists(final_json_path):
            with open(final_json_path, 'r', encoding='utf-8') as f:
                final_data = json.load(f)
        elif cmk_json_files:
            with open(latest_cmk_file, 'r', encoding='utf-8') as f:
                final_data = json.load(f)
        
        # Create row mapping
        row_to_index = {row + 2: row for row in range(len(original_df))}
        
        # Add new columns for additional CoinMarketCap data
        new_columns = [
            "MarketCap", "CirculatingSupply", "MaxSupply", "Volume24h", 
            "PercentChange24h", "PercentChange7d", "PercentChange30d", 
            "Network", "Slug", "DateAdded", "Tags"
        ]
        
        for col in new_columns:
            if col not in original_df.columns:
                original_df[col] = None
        
        # Update the DataFrame with final data
        update_count = 0
        for item in final_data:
            row_num = item.get('Row')
            if row_num not in row_to_index:
                continue
                
            index = row_to_index[row_num]
            
            # Update all columns
            for field, value in item.items():
                if field == "Row":
                    continue
                    
                # Try to find matching column
                matching_cols = [col for col in original_df.columns if col.lower() == field.lower()]
                
                if matching_cols:
                    col = matching_cols[0]
                    # Only update if value is meaningful
                    if value not in ["Not found", ""]:
                        original_df.at[index, col] = value
                        update_count += 1
        
        # Save final Excel
        final_excel_path = f"crypto_data_complete_{final_timestamp}.xlsx"
        original_df.to_excel(final_excel_path, sheet_name="Assets missing info", index=False)
        
        print(f"Updated {update_count} cells in final Excel file")
        print(f"Saved final Excel to {final_excel_path}")
        
    except Exception as e:
        print(f"Error in CoinMarketCap processing: {str(e)}")


if __name__ == "__main__":
    combined_crypto_workflow()
