import cv2
import numpy as np
import pytesseract
import uvicorn
from pytesseract import Output
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from db.database import registerDatabase, getFormattedItems, deleteItem

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
        return None,
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0) 

    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None, "Nenhum contorno fechado detectado."

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
        print("AVISO: OCR falhou. Usando escala 1:1.")
    else:
        x_rect, y_rect, w_rect, h_rect = cv2.boundingRect(approx_polygon)
        max_pixel_dimension = max(w_rect, h_rect)
        max_real_dimension = max(detected_values)
        
        if max_real_dimension > 0:
            scale_factor = max_pixel_dimension / max_real_dimension

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
    lines = []

    print(vertices)
    
    filename = params.get('fileName', 'output.nc')
    safe_z = params.get('safetyZ', 50.0)      
    retract_z = 5.0                           
    feed_cut = params.get('feedRate', 800.0)  
    feed_plunge = feed_cut * 0.3              
    spindle = params.get('spindleSpeed', 1500)
    
    total_thickness = abs(params.get('thickness', 10.0))
    step_down = abs(params.get('stepDown', 2.0))
    
    final_z = -(total_thickness + 0.5) 
    
    safe_entry_x = -20.0
    safe_entry_y = -20.0

    lines.append(f"O1001 ({filename})")
    lines.append(f"{params.get('units', 'G21')} ; Milimetros")
    lines.append("G17 G40 G49 G80 G90 ; Config de Seguranca")
    
    lines.append("T1 M6 ; Troca Ferramenta 1")
    lines.append("G54 ; Offset de Trabalho")
    lines.append(f"S{spindle} M3 ; Liga Spindle")
    lines.append("M8 ; Liga Refrigerante")
    
    lines.append(f"G00 X{safe_entry_x:.3f} Y{safe_entry_y:.3f} ; Ponto de espera seguro")
    lines.append(f"G43 H1 Z{safe_z} ; Compensa Altura")
    lines.append(f"G00 Z{retract_z} ; Desce rapido para perto da peca")

    current_z = 0.0
    
    while current_z > final_z:
        current_z -= step_down
        if current_z < final_z:
            current_z = final_z
            
        lines.append(f"; --- Passada Z = {current_z:.2f} ---")
        
        lines.append(f"G00 X{safe_entry_x:.3f} Y{safe_entry_y:.3f}")
        
        lines.append(f"G01 Z{current_z:.3f} F{feed_plunge:.1f}")
        
        start_pt = vertices[0]
        lines.append(f"G01 G41 D1 X{start_pt['x']:.3f} Y{start_pt['y']:.3f} F{feed_cut:.1f}")
        
        for pt in vertices[1:]:
            lines.append(f"G01 X{pt['x']:.3f} Y{pt['y']:.3f}")
            
        lines.append(f"G01 X{start_pt['x']:.3f} Y{start_pt['y']:.3f}")
        
        lines.append("G01 X0.000 Y0.000")
        lines.append(f"G01 X{safe_entry_x:.3f} Y{safe_entry_y:.3f}")
        lines.append("G40 ; Cancela compensacao")
        
        lines.append(f"G00 Z{retract_z} ; Retracao entre passes")

    lines.append("M9 ; Desliga Refrigerante")
    lines.append("M5 ; Desliga Spindle")
    lines.append(f"G00 Z{safe_z} ; Sobe Z total")
    lines.append("G91 G28 Z0. ; Home Z")
    lines.append("G28 X0. Y0. ; Home Mesa")
    lines.append("M30 ; Fim")
    
    return '\n'.join(lines)

def processToGcode(image_bytes: bytes, form_data: dict):
    vertices, error = processImage(image_bytes)
    
    if error:
        return f"Erro: {error}"
    
    gcode_params = {
        'fileName': form_data.get('filename', 'peca.nc'),
        'units': form_data.get('units', 'G21'),
        'spindleSpeed': int(form_data.get('spindleSpeed', 1500)),
        'safetyZ': float(form_data.get('safetyZ', 50.0)),
        'feedRate': float(form_data.get('feedRate', 800)),
        
        'thickness': float(form_data.get('thickness', 10.0)),   
        'stepDown': float(form_data.get('stepDown', 2.0)) 
    }

    result_gcode = generateGcode(vertices, gcode_params)
    return result_gcode

@app.post("/api/generate-gcode")
async def create_gcode(
    file: UploadFile = File(...), 
    units: str = Form("G21"),
    spindleSpeed: int = Form(1500),
    feedRate: float = Form(800),
    safetyZ: float = Form(50),
    thickness: float = Form(10.0), 
    stepDown: float = Form(2.0)     
):
    
    image_bytes = await file.read()
    
    params_form = {
        "filename": file.filename,
        "units": units,
        "spindleSpeed": spindleSpeed,
        "feedRate": feedRate,
        "safetyZ": safetyZ,
        "thickness": thickness,
        "stepDown": stepDown
    }

    gCode = processToGcode(image_bytes, params_form)
    
    registerDatabase(params_form, gCode)
    
    return gCode

@app.get("/api/history")
def get_history():
    """Retorna a lista formatada para a sidebar"""
    history = getFormattedItems(limit=20)
    return history

# ROTA 3: Deletar Histórico (Opcional, mas útil)
@app.delete("/api/history/{item_id}")
def delete_history(item_id: str):
    success = deleteItem(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return {"message": "Item deletado com sucesso"}

@app.get("/api/healthcheck", tags=["Health"])
def health_check():
    return "API ativa"

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
    
if __name__ == "__main__":
    
    mock_form_data = {
        'thickness': 2, 
        'feedrate': 400,
        'spindle': 1500,
        'filename': 'teste_tcc.nc'
    }

    try:
        # Carrega uma imagem de teste
        with open("../uploads/image1.png", "rb") as f:
            image_bytes = f.read()
        
        # Chama a função orquestradora
        gcode = processToGcode(image_bytes, mock_form_data)
        
        print("\n--- G-CODE GERADO ---\n")
        print(gcode)
        
        # Salva em arquivo
        with open("output_final.nc", "w") as f:
            f.write(gcode)
            
    except FileNotFoundError:
        print("Erro: Imagem de teste não encontrada.")