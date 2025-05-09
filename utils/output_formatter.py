"""
Output formatter for converting extracted data to various formats.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Union
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_text_output(text_data: Dict, output_path: Union[str, Path]) -> Path:
    """Format and save text extraction output as JSON.
    
    Args:
        text_data: Dictionary with extracted text data
        output_path: Path to save the output file
        
    Returns:
        Path to the saved output file
    """
    output_path = Path(output_path)
    
    try:
        # Ensure the output directory exists
        output_path.parent.mkdir(exist_ok=True, parents=True)
        
        # Format the text data with proper structure
        formatted_data = {
            "headers": [],
            "content": []
        }
        
        # If text_data is already structured with headers/content
        if isinstance(text_data, dict):
            if "headers" in text_data:
                formatted_data["headers"] = text_data["headers"]
            if "content" in text_data:
                formatted_data["content"] = text_data["content"]
            elif "text" in text_data:
                formatted_data["content"] = [text_data["text"]]
        else:
            # Fallback for unstructured text
            formatted_data["content"] = [text_data]
        
        # Save as JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(formatted_data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved formatted text output to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error formatting text output: {e}")
        return None

def format_table_output(table_data: List[Dict], output_path: Union[str, Path]) -> Path:
    """Format and save table extraction output as Excel.
    
    Args:
        table_data: List of dictionaries with extracted table data
        output_path: Path to save the output file
        
    Returns:
        Path to the saved output file
    """
    output_path = Path(output_path)
    
    try:
        # Ensure the output directory exists
        output_path.parent.mkdir(exist_ok=True, parents=True)
        
        # Create Excel writer
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Process each table
            for i, table in enumerate(table_data):
                page_num = table.get("page", i + 1)
                table_content = table.get("data", {})
                
                # Handle different table formats from LLM
                if isinstance(table_content, list):
                    # Assuming list of rows
                    df = pd.DataFrame(table_content)
                elif isinstance(table_content, dict):
                    if "rows" in table_content:
                        # Structured with rows
                        df = pd.DataFrame(table_content["rows"])
                    elif "data" in table_content:
                        # Structured with data
                        df = pd.DataFrame(table_content["data"])
                    elif "headers" in table_content and "values" in table_content:
                        # Structured with headers and values
                        df = pd.DataFrame(table_content["values"], columns=table_content["headers"])
                    else:
                        # Try to convert the dict to a dataframe directly
                        try:
                            df = pd.DataFrame.from_dict(table_content)
                        except Exception:
                            logger.warning(f"Could not convert table data to DataFrame: {table_content}")
                            df = pd.DataFrame({"Error": ["Could not parse table data"]})
                else:
                    logger.warning(f"Unexpected table data format: {type(table_content)}")
                    df = pd.DataFrame({"Error": ["Unexpected table data format"]})
                
                # Save to Excel sheet
                sheet_name = f"Page {page_num}"
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Auto-adjust column widths
                for column in df:
                    column_width = max(df[column].astype(str).map(len).max(), len(column))
                    col_idx = df.columns.get_loc(column)
                    writer.sheets[sheet_name].column_dimensions[chr(65 + col_idx)].width = column_width + 2
        
        logger.info(f"Saved formatted table output to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error formatting table output: {e}")
        return None

def convert_json_to_excel(json_path: Union[str, Path], excel_path: Union[str, Path] = None) -> Path:
    """Convert a JSON file to Excel format.
    
    Args:
        json_path: Path to the JSON file
        excel_path: Path to save the Excel file (optional)
        
    Returns:
        Path to the saved Excel file
    """
    json_path = Path(json_path)
    
    if excel_path is None:
        excel_path = json_path.with_suffix('.xlsx')
    else:
        excel_path = Path(excel_path)
        
    try:
        # Load JSON data
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Convert to DataFrame
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # Try to convert nested structure to DataFrame
            if "headers" in data and "content" in data:
                # Special case for our text extraction format
                headers_df = pd.DataFrame({"Headers": data["headers"]})
                content_df = pd.DataFrame({"Content": data["content"]})
                
                # Save to Excel with multiple sheets
                with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                    headers_df.to_excel(writer, sheet_name="Headers", index=False)
                    content_df.to_excel(writer, sheet_name="Content", index=False)
                    
                logger.info(f"Converted JSON to Excel and saved to {excel_path}")
                return excel_path
            else:
                # Try to flatten the dict structure
                df = pd.DataFrame.from_dict(data, orient='index').reset_index()
                df.columns = ['Key', 'Value']
        else:
            raise ValueError(f"Unexpected JSON data format: {type(data)}")
            
        # Save to Excel
        df.to_excel(excel_path, index=False)
        
        logger.info(f"Converted JSON to Excel and saved to {excel_path}")
        return excel_path
        
    except Exception as e:
        logger.error(f"Error converting JSON to Excel: {e}")
        return None