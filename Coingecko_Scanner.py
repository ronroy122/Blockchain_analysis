import pandas as pd
import requests
import time
import json


def find_missing_symbols(excel_file):
    """
    reads an Excel file, extracts cryptocurrency information for rows with names but missing symbols
    returns a list of dictionaries with the results.
    """
    # Read the Excel file
    df = pd.read_excel(excel_file, sheet_name="Assets missing info")

    # Create a list to store the results
    results = []

    # Iterate through the rows
    for index, row in df.iterrows():
        # Check if there's a name but no symbol OR if there's a symbol but no address/blockchain
        if (pd.notna(row.get('Name')) and pd.isna(row.get('Symbol'))) or \
                (pd.notna(row.get('Name')) and pd.notna(row.get('Symbol')) and (
                        pd.isna(row.get('Blockchain')) or pd.isna(row.get('Address')))):
            name = row['Name']
            symbol = row.get('Symbol') if pd.notna(row.get('Symbol')) else None
            row_num = index + 2  # Add 2 for Excel row number (1-based + header)

            # Single print statement showing which row and what we're searching for
            if symbol:
                print(f"Processing row {row_num}: Searching for address/blockchain for '{name}' ({symbol})")
            else:
                print(f"Processing row {row_num}: Searching for information for '{name}'")

            try:
                # Search for the currency by name using CoinGecko API
                search_response = requests.get(
                    "https://api.coingecko.com/api/v3/search",
                    params={"query": name}
                )

                # Handle rate limiting
                if search_response.status_code == 429:
                    time.sleep(60)
                    search_response = requests.get(
                        "https://api.coingecko.com/api/v3/search",
                        params={"query": name}
                    )

                # Process search results
                if search_response.status_code == 200:
                    search_data = search_response.json()

                    if search_data.get('coins') and len(search_data['coins']) > 0:
                        # Get information about the currency
                        coin = search_data['coins'][0]
                        coin_id = coin['id']
                        symbol = symbol or coin['symbol'].upper()  # Use existing symbol if available

                        # Get detailed information about the currency
                        coin_response = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}")

                        # Handle rate limiting
                        if coin_response.status_code == 429:
                            time.sleep(60)
                            coin_response = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}")

                        if coin_response.status_code == 200:
                            coin_data = coin_response.json()

                            # Get price
                            price = coin_data.get('market_data', {}).get('current_price', {}).get('usd',
                                                                                                  'Not available')
                            
                            # Add dollar sign to price if it's a number
                            if price != 'Not available':
                                price = f"${price}"

                            # Get blockchain and address
                            platforms = coin_data.get('platforms', {})
                            blockchain = "Not available"
                            address = "Not available"

                            # Find the first valid blockchain and address
                            for bc, addr in platforms.items():
                                if addr:
                                    blockchain = bc
                                    address = addr
                                    break

                            # Add to results
                            results.append({
                                "Row": row_num,
                                "Name": name,
                                "Symbol": symbol,
                                "Blockchain": blockchain,
                                "Address": address,
                                "Price": price
                            })
                        else:
                            # API error for detailed information
                            results.append({
                                "Row": row_num,
                                "Name": name,
                                "Symbol": symbol,
                                "Blockchain": "Not available",
                                "Address": "Not available",
                                "Price": "Not available",
                                "Reason": f"API error: {coin_response.status_code}"
                            })
                    else:
                        # No currency found
                        results.append({
                            "Row": row_num,
                            "Name": name,
                            "Symbol": "Not found",
                            "Blockchain": "Not available",
                            "Address": "Not available",
                            "Price": "Not available",
                            "Reason": "Symbol not found"
                        })
                else:
                    # API error in search
                    results.append({
                        "Row": row_num,
                        "Name": name,
                        "Symbol": "Error",
                        "Blockchain": "Not available",
                        "Address": "Not available",
                        "Price": "Not available",
                        "Reason": f"API error: {search_response.status_code}"
                    })

                # Wait to respect API rate limits
                time.sleep(1.5)

            except Exception as e:
                # An error occurred
                results.append({
                    "Row": row_num,
                    "Name": name,
                    "Symbol": "Error",
                    "Blockchain": "Not available",
                    "Address": "Not available",
                    "Price": "Not available",
                    "Reason": f"Error: {str(e)}"
                })

    return results


def coingecko():
    """
    Main function to process missing symbols using CoinGecko API
    """
    file_path = "Fireblocks_Task__-_assets_with_missing_info.xlsx"
    missing_info = find_missing_symbols(file_path)

    # Print the results
    print("\n===== Missing Information Search Results =====\n")
    for item in missing_info:
        print(f"Row: {item['Row']}, Name: {item['Name']}, Symbol: {item['Symbol']}")
        print(f"Blockchain: {item['Blockchain']}, Address: {item['Address']}, Price: {item['Price']}")
        if 'Reason' in item:
            print(f"Reason: {item['Reason']}")
        print("-" * 50)

    # Save the results to a JSON file
    with open("missing_symbols_results.json", "w", encoding="utf-8") as f:
        json.dump(missing_info, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to file: missing_symbols_results.json")


# Usage example
if __name__ == "__main__":
    coingecko()