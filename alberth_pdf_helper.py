# /// script
# dependencies = [
#     "pypdf",
# ]
# ///

import os
import sys
import glob
import re
from datetime import datetime

def find_pdf_files():
    home = os.path.expanduser("~")
    downloads_dir = os.path.join(home, "Downloads")
    desktop_dir = os.path.join(home, "Desktop")
    
    pdf_files = []
    
    # Scan Downloads
    for path in glob.glob(os.path.join(downloads_dir, "*.pdf")):
        if os.path.isfile(path):
            pdf_files.append((path, os.path.getmtime(path)))
            
    # Scan Desktop
    for path in glob.glob(os.path.join(desktop_dir, "*.pdf")):
        if os.path.isfile(path):
            pdf_files.append((path, os.path.getmtime(path)))
            
    # Sort by modification time descending
    pdf_files.sort(key=lambda x: x[1], reverse=True)
    return pdf_files

def match_pdf_by_query(query, pdf_files):
    if not query:
        return None
        
    # Clean query and look for words that might be in the filename
    # Remove common words and search terms
    cleaned_query = query.lower()
    cleaned_query = re.sub(r'\b(resumí|resume|este|el|la|los|un|pdf|archivo|documento|por|favor|de|para|con)\b', ' ', cleaned_query)
    words = [w.strip() for w in re.split(r'\s+', cleaned_query) if len(w.strip()) > 2]
    
    if not words:
        return None
        
    # Find the best match
    best_match = None
    best_score = 0
    
    for path, mtime in pdf_files:
        filename = os.path.basename(path).lower()
        score = sum(1 for word in words if word in filename)
        if score > best_score:
            best_score = score
            best_match = path
            
    if best_score > 0:
        return best_match
    return None

def extract_text_from_pdf(pdf_path, max_pages=10, max_chars=8000):
    try:
        reader = pypdf.PdfReader(pdf_path)
        num_pages = len(reader.pages)
        
        extracted_text = []
        char_count = 0
        
        pages_to_read = min(num_pages, max_pages)
        for i in range(pages_to_read):
            page_text = reader.pages[i].extract_text() or ""
            extracted_text.append(f"--- PÁGINA {i+1} ---")
            extracted_text.append(page_text)
            char_count += len(page_text)
            if char_count > max_chars:
                extracted_text.append("\n[Lectura truncada por longitud del documento]")
                break
                
        text = "\n".join(extracted_text).strip()
        
        # Check if we got basically no text
        clean_text = re.sub(r'\s+', '', text)
        if len(clean_text) < 50:
            return None, "El archivo parece estar vacío o compuesto principalmente por imágenes escaneadas (sin capa de texto)."
            
        return text, None
    except Exception as e:
        return None, f"Error al leer el archivo PDF: {str(e)}"

def main():
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    
    # 1. Find all PDFs
    pdf_files = find_pdf_files()
    if not pdf_files:
        print("ERROR: No se encontró ningún archivo PDF en las carpetas Downloads o Desktop.")
        sys.exit(1)
        
    # 2. Try to match by query keywords
    selected_pdf = match_pdf_by_query(query, pdf_files)
    
    # 3. Fallback to the most recent PDF
    if not selected_pdf:
        selected_pdf = pdf_files[0][0]
        
    filename = os.path.basename(selected_pdf)
    mod_time = datetime.fromtimestamp(os.path.getmtime(selected_pdf)).strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"ARCHIVO_SELECCIONADO: {selected_pdf}")
    print(f"NOMBRE: {filename}")
    print(f"FECHA_MODIFICACION: {mod_time}")
    print("=" * 40)
    
    # 4. Extract text
    text, error = extract_text_from_pdf(selected_pdf)
    if error:
        print(f"ERROR: {error}")
        sys.exit(2)
        
    print(text)

if __name__ == "__main__":
    # Import pypdf inside to let uv handle it dynamically
    try:
        import pypdf
    except ImportError:
        print("ERROR: pypdf no está instalado.")
        sys.exit(3)
    main()
