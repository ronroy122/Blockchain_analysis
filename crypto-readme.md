# Cryptocurrency Data Collection System

A system for collecting and integrating cryptocurrency data from various sources.

## Quick Start Guide

```
# Install required dependencies
pip install -r requirements.txt

# Option 1: Run the main combined workflow (requires API calls):
python Combine_Scanners_to_Excel.py

# Option 2: Use pre-generated JSON files to save time (fastest):
python Combine_Scanners_to_Excel.py
# When prompted "Do you want to run data collection", enter 'n'
```

The repository includes pre-generated JSON and Excel files from previous runs, 
which you can use to skip time-consuming API calls and test the system quickly.

You will need a CoinMarketCap API key for the final enrichment step if running option 1.

Alternatively, you can run individual scanners separately:
- `python Coingecko_Scanner.py` - For basic data from CoinGecko
- `python Eth_Bnb_Scanner.py` - For Ethereum/BSC token data
- `python Coinmarketcap_Scanner.py` - For comprehensive market data (requires API key)

## System Purpose

This system is designed to handle missing information in cryptocurrency asset Excel files. It collects and completes information such as symbols, contract addresses, prices, and additional data from several online sources:
- CoinGecko API
- Blockchain explorers (Etherscan and BSCScan)
- CoinMarketCap API

## System Files

The system consists of four main scripts:

1. **Coingecko_Scanner.py**: Searches for missing information using the CoinGecko API
2. **Eth_Bnb_Scanner.py**: Extracts token information from Etherscan and BSCScan websites
3. **Coinmarketcap_Scanner.py**: Enriches cryptocurrency data using the CoinMarketCap API
4. **Combine_Scanners_to_Excel.py**: Combines all collected information into one Excel file

## Prerequisites

```
pandas==1.3.0
requests==2.26.0
beautifulsoup4==4.9.3
```

You can install all required libraries using:

```bash
pip install -r requirements.txt
```

## Input File

The system works with an Excel file named `Fireblocks_Task__-_assets_with_missing_info.xlsx` containing a sheet named "Assets missing info".
This sheet should contain columns with information about cryptocurrencies, such as name, symbol, blockchain network, and contract address.

## Usage

### Using Each Scanner Separately

#### Scanning with CoinGecko
```python
python Coingecko_Scanner.py
```
The script will read the Excel file, search for missing information using the CoinGecko API, and save the results to a JSON file.

#### Scanning with Etherscan/BSCScan
```python
python Eth_Bnb_Scanner.py
```
The script will read the Excel file, scan the Etherscan and BSCScan websites to find token information, and save the results to a JSON file.

#### Scanning with CoinMarketCap
```python
python Coinmarketcap_Scanner.py
```
The script will read the Excel file, ask for your CoinMarketCap API key, and enrich the data using the API.

### Using the Combined System

```python
python Combine_Scanners_to_Excel.py
```

This script runs the complete process:
1. Running the CoinGecko and Etherscan/BSCScan scanners (optional)
2. Merging the collected data
3. Creating an intermediate Excel file with the combined data
4. Enriching the data using the CoinMarketCap API (requires an API key)
5. Creating a final Excel file with all collected information

## Recommended Workflow

1. Prepare your Excel file with missing cryptocurrency data
2. Obtain a CoinMarketCap API key (required for the final stage)
3. Run `Combine_Scanners_to_Excel.py` for the complete collection and merging process
4. Check the final Excel file created with the combined information

## Output Files

The system generates several output files:
- **missing_symbols_results.json**: Results from CoinGecko scanning
- **token_info_results.json**: Results from Etherscan/BSCScan scanning
- **intermediate_crypto_data_[timestamp].xlsx**: Intermediate Excel file before CoinMarketCap enrichment
- **crypto_data_final_[timestamp].json**: Final results from CoinMarketCap scanning
- **crypto_data_complete_[timestamp].xlsx**: Final Excel file with all combined information

## Notes and Warnings

1. **API Limitations**: Be aware of the rate limits of the APIs. CoinGecko and CoinMarketCap limit the number of calls that can be made in a given time.
2. **Web Scraping**: The Etherscan/BSCScan scanner relies on the current structure of the websites. Changes to the website structure may affect the script's operation.
3. **Runtime**: The complete collection process may take time, especially for large lists of currencies, due to the wait times between API calls.

## Using Pre-Generated Output Files

The repository includes several pre-generated output files:

### JSON Files:
- **missing_symbols_results.json**: From CoinGecko
- **token_info_results.json**: From Etherscan/BSCScan
- **merged_crypto_data_[timestamp].json**: Combined data from multiple sources

### Excel Files:
- **crypto_data_complete_[timestamp].xlsx**: Final output with all data integrated

When using the combined workflow script, select 'n' when asked to run data collection to use these existing files.

## Troubleshooting

- If you encounter API errors, try increasing the wait times between calls
- If Etherscan/BSCScan collection fails, there may be a change in the website structure
- For CoinMarketCap, ensure your API key is valid and has the appropriate permissions

## Possible Future Improvements

1. Adding support for additional blockchain platforms
2. Improving API error handling
3. Adding a graphical user interface
4. Optimizing runtimes using parallel processes
5. Adding more information sources

---

Created in 2025 - All Rights Reserved
