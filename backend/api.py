import cv2
import numpy as np
import pytesseract
import uvicorn
from pytesseract import Output
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import registerDatabase
import math

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def processImage(image_bytes: bytes):

    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return None, "Imagem inválida ou corrompida."
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0) 

    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None, "Nenhum contorno fechado detectado. Tente uma imagem com traço mais grosso/escuro."

    largest_contour = max(contours, key=cv2.contourArea)
    
    epsilon = 0.01 * cv2.arcLength(largest_contour, True)
    approx_polygon = cv2.approxPolyDP(largest_contour, epsilon, True)

    custom_config = r'--oem 3 --psm 11 -c tessedit_char_whitelist=0123456789'
    d = pytesseract.image_to_data(gray, config=custom_config, output_type=Output.DICT)
    
    detected_values = []
    
    for i in range(len(d['text'])):
        text = d['text'][i].strip()
        if text.isdigit():
            val = int(text)
            if val > 0:
                detected_values.append(val)
    
    scale_factor = 1.0 
    
    if not detected_values:
        print("AVISO: Nenhuma cota numérica encontrada via OCR. Usando escala 1:1.")
    else:

        x_rect, y_rect, w_rect, h_rect = cv2.boundingRect(approx_polygon)
        max_pixel_dimension = max(w_rect, h_rect)
        max_real_dimension = max(detected_values)
        
       
        if max_real_dimension > 0:
            scale_factor = max_pixel_dimension / max_real_dimension
            print(f"--- INFO ESCALA ---")
            print(f"Maior lado em Pixels: {max_pixel_dimension}")
            print(f"Maior cota (OCR): {max_real_dimension}")
            print(f"Fator de Escala: {scale_factor:.4f} px/mm")

    
    points_px = approx_polygon.reshape(-1, 2) 
    
  
    min_x_px = np.min(points_px[:, 0])
    max_y_px = np.max(points_px[:, 1]) 
    
    final_vertices = []
    
    for pt in points_px:
 
        vx = (pt[0] - min_x_px) / scale_factor
        
        vy = (max_y_px - pt[1]) / scale_factor
        
        final_vertices.append({'x': vx, 'y': vy})

    return final_vertices, None

def generateGcode(vertices: list, params: dict):

    gcode_lines = []
    
    
    safe_z = params.get('safetyZ', 5.0)
    feed = params.get('feedRate', 300.0)
    spindle = params.get('spindleSpeed', 1200)
    
    cut_depth = params.get('cutDepth', -1.0) 
    
    gcode_lines.append(f"({params.get('fileName', 'output.nc')})")
    gcode_lines.append(f"{params.get('units', 'G21')} ; Define milimetros")
    gcode_lines.append("G90 ; Coordenadas absolutas")
    gcode_lines.append("G17 ; Plano XY")
    gcode_lines.append(f"M03 S{spindle} ; Liga spindle")
    gcode_lines.append(f"G00 Z{safe_z} ; Z de seguranca")
    
    if not vertices:
        gcode_lines.append("(ERRO: Nenhum vértice processado)")
        return "\n".join(gcode_lines)

    start_pt = vertices[0]
    gcode_lines.append(f"G00 X{start_pt['x']:.3f} Y{start_pt['y']:.3f}")
    
    gcode_lines.append(f"G01 Z{cut_depth} F{feed/2:.1f}")
    
    for point in vertices[1:]:
        gcode_lines.append(f"G01 X{point['x']:.3f} Y{point['y']:.3f} F{feed}")
        
    gcode_lines.append(f"G01 X{start_pt['x']:.3f} Y{start_pt['y']:.3f}")
      
    gcode_lines.append(f"G00 Z{safe_z} ; Sobe ferramenta")
    gcode_lines.append("M05 ; Desliga spindle")
    gcode_lines.append("M30 ; Fim de programa")
    
    return '\n'.join(gcode_lines)

def processToGcode(image_bytes: bytes, form_data: dict):
    
    
    vertices, error = processImage(image_bytes)
    
    if error:
        return f"Erro: {error}"
    
   
    thickness = float(form_data.get('thickness', 0)) 
    cut_depth = -abs(float(form_data.get('cutDepth', 1.0))) if float(form_data.get('cutDepth', 0)) != 0 else -1.0
    
    gcode_params = {
        'fileName': form_data.get('filename', 'peca.nc'),
        'units': form_data.get('units', 'G21'),
        'spindleSpeed': form_data.get('spindleSpeed', 1200),
        'safetyZ': float(form_data.get('safetyZ', 5.0)),
        'cutDepth': cut_depth,
        'feedRate': float(form_data.get('feedRate', 300))
    }

    result_gcode = generateGcode(vertices, gcode_params)
    
    return result_gcode


@app.post("/api/generate-gcode")
async def create_gcode(
    
    file: UploadFile = File(...), 
    units: str = Form(...),
    spindleSpeed: int = Form(...),
    feedRate: float = Form(...),
    safetyZ: float = Form(...),
    cutDepth: float = Form(...)):
    
    image_bytes = await file.read()

    params = {
        "fileName": file.filename,
        "units": units,
        "spindleSpeed": spindleSpeed,
        "feedRate": feedRate,
        "safetyZ": safetyZ,
        "cutDepth": cutDepth
    }

    gCode = processToGcode(image_bytes, params)
    
    registerDatabase(params, gCode)
    
    return gCode

@app.get("/api/healthcheck", tags=["Health"])
def health_check():
    return "API Ativa!"

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

# =============================================================================
# 5. EXEMPLO DE USO (SIMULAÇÃO DO BACKEND)
# =============================================================================

# if __name__ == "__main__":
#     # Simulação dos dados que viriam do seu Frontend (React/Flask request)
#     mock_form_data = {
#         'thickness': 15.0,   # <--- ESPESSURA DA PEÇA AQUI
#         'feedrate': 400,
#         'spindle': 1500,
#         'filename': 'teste_tcc.nc'
#     }

#     try:
#         # Carrega uma imagem de teste
#         with open("imagetest.png", "rb") as f:
#             image_bytes = f.read()
        
#         # Chama a função orquestradora
#         gcode = processToGcode(image_bytes, mock_form_data)
        
#         print("\n--- G-CODE GERADO ---\n")
#         print(gcode)
        
#         # Salva em arquivo
#         with open("output_final.nc", "w") as f:
#             f.write(gcode)
            
#     except FileNotFoundError:
#         print("Erro: Imagem de teste não encontrada.")