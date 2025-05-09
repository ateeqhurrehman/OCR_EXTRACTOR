"""
Streamlit frontend for the OCR document extraction system.
"""
import os
import json
import logging
import requests
import pandas as pd
import streamlit as st
from pathlib import Path
import time
import base64
from PIL import Image
import io

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
API_URL = "http://127.0.0.1:5000"  # Flask server URL
ALLOWED_EXTENSIONS = ["pdf", "jpg", "jpeg", "png", "tiff", "docx"]

# Set page configuration
st.set_page_config(
    page_title="Document OCR System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Helper functions
def get_file_extension(filename):
    """Get the file extension from a filename."""
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""

def is_allowed_file(filename):
    """Check if a file has an allowed extension."""
    return get_file_extension(filename) in ALLOWED_EXTENSIONS

def display_json(json_data):
    """Display JSON data in a formatted way."""
    st.json(json_data)

def display_file_content(file_path):
    """Display file content based on file type."""
    ext = file_path.suffix.lower()[1:]
    
    if ext == "json":
        with open(file_path, "r") as f:
            data = json.load(f)
        st.subheader("JSON Data")
        st.json(data)
        
    elif ext == "xlsx":
        st.subheader("Excel Data")
        df = pd.read_excel(file_path, sheet_name=None)
        
        # Display each sheet in the Excel file
        for sheet_name, sheet_df in df.items():
            st.write(f"**Sheet: {sheet_name}**")
            st.dataframe(sheet_df)
            
    elif ext in ["jpg", "jpeg", "png"]:
        st.subheader("Image")
        st.image(file_path)
        
    else:
        st.write(f"Cannot display content for file type: {ext}")

def get_binary_file_downloader_html(file_path, file_label="File"):
    """Generate HTML for downloading files."""
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{os.path.basename(file_path)}">{file_label}</a>'
    return href

# Sidebar
st.sidebar.title("Document OCR System")
st.sidebar.info(
    "This application extracts text and structured data from documents using "
    "a local LLM (gemma3:4b) through Ollama. It can process PDFs, images, and DOCX files."
)

# Check if Flask server is running
@st.cache_data(ttl=5)
def check_server_status():
    try:
        response = requests.get(f"{API_URL}/status")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

if not check_server_status():
    st.error(
        "Flask server is not running. Please start the server using: "
        "`python server.py`"
    )
    st.stop()

# Main content
st.title("Document OCR Extraction")

# File upload
st.header("Upload Document")
uploaded_file = st.file_uploader(
    "Choose a document file", 
    type=ALLOWED_EXTENSIONS,
    help="Upload a PDF, image, or DOCX file to extract text and data"
)

if uploaded_file is not None:
    # Display file details
    file_size_kb = uploaded_file.size / 1024
    file_type = get_file_extension(uploaded_file.name)
    
    st.write(f"Uploaded file: **{uploaded_file.name}** ({file_size_kb:.2f} KB)")
    
    # Create a progress bar for processing
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Show the uploaded file
    if file_type in ["jpg", "jpeg", "png", "tiff"]:
        st.subheader("Uploaded Image")
        image = Image.open(uploaded_file)
        st.image(image, caption=uploaded_file.name, use_column_width=True)
    elif file_type == "pdf":
        st.subheader("Uploaded PDF")
        st.write("PDF preview not available. Processing will convert PDF pages to images.")
    elif file_type == "docx":
        st.subheader("Uploaded DOCX")
        st.write("DOCX preview not available. Processing will convert DOCX pages to images.")
    
    # Process button
    if st.button("Process Document"):
        status_text.text("Uploading document...")
        progress_bar.progress(10)
        
        # Send file to Flask API for processing
        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
        
        try:
            status_text.text("Processing document with LLM...")
            progress_bar.progress(30)
            
            # Send to processing endpoint
            response = requests.post(f"{API_URL}/upload", files=files)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("success", False):
                    progress_bar.progress(90)
                    status_text.text("Processing complete!")
                    progress_bar.progress(100)
                    
                    # Display results
                    st.header("Extraction Results")
                    
                    document_type = result.get("document_type", "unknown")
                    st.write(f"Document Type: **{document_type}**")
                    
                    # Display tabs for different outputs
                    tabs = st.tabs(["Text Output", "Table Output (if available)", "Screenshots", "Raw Results"])
                    
                    # Tab 1: Text Output
                    with tabs[0]:
                        text_output_path = result.get("text_output_path")
                        if text_output_path:
                            # Fetch the JSON content
                            try:
                                json_response = requests.get(f"{API_URL}/output/{os.path.basename(text_output_path)}")
                                if json_response.status_code == 200:
                                    st.subheader("Extracted Text Content")
                                    json_data = json_response.json()
                                    
                                    # Display headers if available
                                    if "headers" in json_data and json_data["headers"]:
                                        st.subheader("Headers")
                                        for i, header in enumerate(json_data["headers"]):
                                            st.write(f"**{i+1}.** {header}")
                                    
                                    # Display content if available
                                    if "content" in json_data and json_data["content"]:
                                        st.subheader("Content")
                                        for i, paragraph in enumerate(json_data["content"]):
                                            st.write(paragraph)
                                            if i < len(json_data["content"]) - 1:
                                                st.write("---")
                                    
                                    # Offer download option
                                    st.download_button(
                                        label="Download JSON",
                                        data=json.dumps(json_data, indent=2),
                                        file_name=f"{uploaded_file.name}.json",
                                        mime="application/json"
                                    )
                            except Exception as e:
                                st.error(f"Error fetching text output: {e}")
                        else:
                            st.write("No text output available")
                    
                    # Tab 2: Table Output
                    with tabs[1]:
                        table_output_path = result.get("table_output_path")
                        if table_output_path:
                            st.subheader("Extracted Table Data")
                            st.write("Table data is available for download as Excel")
                            
                            # Create download link
                            table_filename = os.path.basename(table_output_path)
                            download_link = f"{API_URL}/output/{table_filename}"
                            st.markdown(f"[Download Excel File]({download_link})")
                            
                            # Try to display table preview
                            try:
                                # We can't directly access the file, but we could implement an API endpoint
                                # to get the Excel data as JSON for preview. For now, we'll skip this.
                                st.info("Table preview not available in this version. Please download the Excel file.")
                            except Exception as e:
                                st.error(f"Error displaying table preview: {e}")
                        else:
                            st.write("No tables detected in the document")
                    
                    # Tab 3: Screenshots 
                    with tabs[2]:
                        screenshot_folder = result.get("screenshot_folder")
                        if screenshot_folder and document_type in ["pdf", "docx"]:
                            st.subheader("Document Screenshots")
                            
                            # Get list of screenshots
                            doc_name = Path(screenshot_folder).name
                            try:
                                files_response = requests.get(f"{API_URL}/files/{uploaded_file.name}")
                                if files_response.status_code == 200:
                                    files_data = files_response.json()
                                    screenshots = files_data.get("screenshots", [])
                                    
                                    if screenshots:
                                        # Display them in a grid
                                        cols = st.columns(3)
                                        for i, screenshot in enumerate(screenshots):
                                            with cols[i % 3]:
                                                screenshot_url = f"{API_URL}/screenshot/{doc_name}/{screenshot}"
                                                st.image(screenshot_url, caption=f"Page {i+1}")
                                    else:
                                        st.write("No screenshots available")
                            except Exception as e:
                                st.error(f"Error fetching screenshots: {e}")
                        elif document_type == "image":
                            st.subheader("Original Image")
                            image = Image.open(uploaded_file)
                            st.image(image, caption=uploaded_file.name, use_column_width=True)
                        else:
                            st.write("No screenshots available")
                    
                    # Tab 4: Raw Results
                    with tabs[3]:
                        st.subheader("Raw Processing Results")
                        st.json(result)
                else:
                    st.error(f"Processing failed: {result.get('error', 'Unknown error')}")
            else:
                st.error(f"API request failed with status code {response.status_code}")
                st.write(response.text)
        
        except Exception as e:
            st.error(f"Error during processing: {e}")
            logger.exception("Error during document processing")
        
        finally:
            # Reset progress
            progress_bar.empty()
            status_text.empty()

# Information about the system
with st.expander("About this OCR System"):
    st.write(
        """
        This document OCR system uses a local LLM (gemma3:4b) through Ollama to extract text and structured 
        data from various document formats. It takes an agentic AI approach to analyze documents and extract 
        information appropriately based on content type.
        
        **Features:**
        - Processes PDFs, images, and DOCX files
        - Extracts text content with headers and sections
        - Identifies and extracts tables to Excel format
        - Handles different document layouts and structures
        - Uses local LLM for privacy and control
        
        **Technical Stack:**
        - Frontend: Streamlit
        - Backend: Flask
        - LLM: Ollama with gemma3:4b
        - Image Processing: Pillow, pdf2image
        - Data Handling: Pandas, JSON
        """
    )

# Footer
st.sidebar.markdown("---")
st.sidebar.info(
    "This is a demo application for document OCR extraction using LLMs. "
    "Developed as a fully functional, self-contained Python project."
)