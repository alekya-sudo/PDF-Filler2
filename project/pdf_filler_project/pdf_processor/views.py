import fitz  # PyMuPDF for PDF parsing
import pytesseract
import cv2
import numpy as np
from pdf2image import convert_from_path
import pandas as pd
import PyPDF2
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import os


# PDF Structure Extraction Function
def extract_pdf_structure(pdf_path):
    """Extracts text structure from a PDF using PyMuPDF."""
    pdf_document = fitz.open(pdf_path)
    text_content = ""
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text_content += page.get_text("text")
    return text_content


# Convert PDF Pages to Images
def pdf_to_images(pdf_path):
    """Converts a PDF to images using pdf2image."""
    images = convert_from_path(pdf_path)
    return images


# OCR Text Extraction from Image
def extract_text_from_image(image):
    """Extracts text from an image using Tesseract OCR."""
    image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    text = pytesseract.image_to_string(image)
    return text


# Parsing Knowledge Database (CSV to Dictionary)
def parse_knowledge_db(db_path):
    """Parses a knowledge database (in CSV format) to a dictionary."""
    data = pd.read_csv(db_path, sep=":", header=None)
    knowledge_dict = dict(zip(data[0], data[1]))
    return knowledge_dict


# Field Data Mapping
def map_fields_to_data(pdf_fields, knowledge_db):
    """Maps PDF fields to knowledge database values."""
    filled_fields = {}
    for field in pdf_fields:
        if field in knowledge_db:
            filled_fields[field] = knowledge_db[field]
    return filled_fields


# Filling the PDF Template
def fill_pdf_template(input_pdf, output_pdf, field_data):
    """Fills a PDF template with data."""
    reader = PyPDF2.PdfReader(input_pdf)
    writer = PyPDF2.PdfWriter()

    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        writer.add_page(page)

        # Get field data (assuming AcroForm fields)
        fields = reader.get_fields()
        
        # Add logging to ensure fields and field_data are not None
        print(f"PDF Fields: {fields}")
        print(f"Filled Data: {field_data}")

        if fields:
            for field in fields:
                if field in field_data:
                    fields[field].update({
                        '/V': field_data[field],
                    })

    # Write the updated PDF to the output file
    with open(output_pdf, 'wb') as output_file:
        writer.write(output_file)


# Django View to Handle PDF Form Filling
def fill_pdf_view(request):
    if request.method == 'POST':
        # Check if files and fields are submitted
        if 'pdf_file' not in request.FILES or 'knowledge_db_file' not in request.FILES:
            return JsonResponse({'error': 'Please upload both PDF file and Knowledge DB file.'})

        # Get the uploaded files
        pdf_file = request.FILES['pdf_file']
        knowledge_db_file = request.FILES['knowledge_db_file']

        # Save the uploaded files temporarily
        pdf_full_path = os.path.join(settings.MEDIA_ROOT, 'uploaded_pdf.pdf')
        knowledge_db_full_path = os.path.join(settings.MEDIA_ROOT, 'knowledge_db.csv')

        with open(pdf_full_path, 'wb+') as destination:
            for chunk in pdf_file.chunks():
                destination.write(chunk)

        with open(knowledge_db_full_path, 'wb+') as destination:
            for chunk in knowledge_db_file.chunks():
                destination.write(chunk)

        # Parse knowledge DB
        knowledge_db = parse_knowledge_db(knowledge_db_full_path)

        # Collect fields from user input (from POST request)
        pdf_fields = request.POST.getlist('field_name[]')
        field_values = request.POST.getlist('field_value[]')
        
        # Map fields to their corresponding data
        filled_data = dict(zip(pdf_fields, field_values))
        print(f"Filled Data: {filled_data}")

        # Ensure filled_data is not None or empty
        if not filled_data:
            return JsonResponse({'error': 'No fields to fill in the PDF.'})

        # Output PDF Path
        output_pdf = os.path.join(settings.MEDIA_ROOT, 'filled_output.pdf')

        # Fill the PDF template
        try:
            fill_pdf_template(pdf_full_path, output_pdf, filled_data)
            return JsonResponse({'message': 'PDF filled successfully!', 'output_pdf': output_pdf})
        except Exception as e:
            return JsonResponse({'error': f"An error occurred while filling the PDF: {str(e)}"})

    return render(request, 'home.html')
