from flask import Flask, request, jsonify, send_from_directory
import os
import tempfile
from PyPDF2 import PdfReader
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static')

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

# Ensure upload directory exists
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def analyze_resume_with_gemini(resume_text, job_description):
    """Analyze the resume with Gemini and return the results."""
    prompt = f"""
    Analyze this resume against the following job description and provide:
    1. A compatibility score (0-100)
    2. A concise summary of the resume
    3. Key strengths in relation to the job
    4. Areas for improvement
    5. Suggestions for better alignment with the job
    
    Return the response in JSON format with these keys: score, summary, strengths, improvements, suggestions.
    
    Resume:
    {resume_text}
    
    Job Description:
    {job_description}
    """
    
    try:
        response = model.generate_content(prompt)
        # The response might need parsing depending on how Gemini returns it
        # This is a simplified approach - you might need to adjust based on actual response format
        if response.text.startswith('```json'):
            # Sometimes Gemini wraps JSON in markdown code blocks
            json_str = response.text[7:-3]  # Remove the ```json and ```
        else:
            json_str = response.text
        
        # Basic cleanup of the response
        json_str = json_str.strip().replace('```', '')
        return json_str
    except Exception as e:
        print(f"Error analyzing with Gemini: {e}")
        return None

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/results.html')
def results():
    return send_from_directory('.', 'results.html')

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    if 'resume' not in request.files:
        return jsonify({'error': 'No resume file uploaded'}), 400
    
    resume_file = request.files['resume']
    job_description = request.form.get('job_description', '')
    
    if resume_file.filename == '':
        return jsonify({'error': 'No selected resume file'}), 400
    
    if not job_description:
        return jsonify({'error': 'Job description is required'}), 400
    
    try:
        # Save the uploaded file temporarily
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        resume_file.save(temp_pdf.name)
        temp_pdf.close()
        
        # Extract text from PDF
        resume_text = extract_text_from_pdf(temp_pdf.name)
        
        # Analyze with Gemini
        analysis_result = analyze_resume_with_gemini(resume_text, job_description)
        
        if not analysis_result:
            return jsonify({'error': 'Failed to analyze resume'}), 500
        
        # Clean up the temporary file
        os.unlink(temp_pdf.name)
        
        return analysis_result
        
    except Exception as e:
        print(f"Error processing resume: {e}")
        if 'temp_pdf' in locals() and os.path.exists(temp_pdf.name):
            os.unlink(temp_pdf.name)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)