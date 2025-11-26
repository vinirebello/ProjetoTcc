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

# --- CONFIGURAÇÕES ---
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# =============================================================================
# 1. FUNÇÕES AUXILIARES MATEMÁTICAS
# =============================================================================

def calculate_distance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def get_line_midpoint(x1, y1, x2, y2):
    return ((x1 + x2) // 2, (y1 + y2) // 2)

# =============================================================================
# 2. VISÃO COMPUTACIONAL (ASSOCIAÇÃO)
# =============================================================================

def process_image_and_generate_geometry(image_bytes: bytes):
    """
    Nova abordagem para TCC:
    1. Detecta o contorno fechado da peça (em vez de linhas soltas).
    2. Simplifica a forma (aprox. poligonal) para gerar vértices limpos.
    3. Lê cotas (OCR) para calcular a escala global (px -> mm).
    """
    # Decodifica a imagem
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return None, "Imagem inválida ou corrompida."
    
    # 1. Pré-processamento
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0) # Remove ruído
    # Binarização (Preto e Branco)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 2. Encontrar Contornos
    # RETR_EXTERNAL: Pega apenas o contorno externo (o perfil da peça)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None, "Nenhum contorno fechado detectado. Tente uma imagem com traço mais grosso/escuro."

    # Assume que a peça é o maior objeto na imagem
    largest_contour = max(contours, key=cv2.contourArea)

    # 3. Aproximação Poligonal (Vértices)
    # Transforma o contorno cheio de pixels em linhas retas (vértices)
    # O fator 0.01 determina a sensibilidade (quanto menor, mais detalhes curva)
    epsilon = 0.01 * cv2.arcLength(largest_contour, True)
    approx_polygon = cv2.approxPolyDP(largest_contour, epsilon, True)

    # approx_polygon agora contém os pontos ordenados (X, Y) em pixels

    # 4. OCR e Cálculo de Escala
    # Configuração para ler números isolados
    custom_config = r'--oem 3 --psm 11 -c tessedit_char_whitelist=0123456789'
    d = pytesseract.image_to_data(gray, config=custom_config, output_type=Output.DICT)
    
    detected_values = []
    # Filtra apenas o que for número e maior que zero
    for i in range(len(d['text'])):
        text = d['text'][i].strip()
        if text.isdigit():
            val = int(text)
            if val > 0:
                detected_values.append(val)
    
    scale_factor = 1.0 # Padrão (1px = 1mm) caso falhe
    
    if not detected_values:
        print("AVISO: Nenhuma cota numérica encontrada via OCR. Usando escala 1:1.")
    else:
        # Lógica de Escala Global:
        # Pega a largura máxima da peça em Pixels e compara com o maior valor lido no OCR.
        x_rect, y_rect, w_rect, h_rect = cv2.boundingRect(approx_polygon)
        max_pixel_dimension = max(w_rect, h_rect)
        max_real_dimension = max(detected_values)
        
        # Evita divisão por zero
        if max_real_dimension > 0:
            scale_factor = max_pixel_dimension / max_real_dimension
            print(f"--- INFO ESCALA ---")
            print(f"Maior lado em Pixels: {max_pixel_dimension}")
            print(f"Maior cota (OCR): {max_real_dimension}")
            print(f"Fator de Escala: {scale_factor:.4f} px/mm")

    # 5. Converter e Normalizar Vértices
    points_px = approx_polygon.reshape(-1, 2) # Formato [[x,y], [x,y]...]
    
    # Encontra os limites para zerar a peça na origem (0,0)
    min_x_px = np.min(points_px[:, 0])
    max_y_px = np.max(points_px[:, 1]) # Usado para inverter o Y
    
    final_vertices = []
    
    for pt in points_px:
        # X: (Posição - Mínimo) / Escala
        vx = (pt[0] - min_x_px) / scale_factor
        
        # Y: Inversão (Imagem cresce pra baixo, CNC pra cima)
        # (Máximo - Posição) / Escala -> Isso coloca a base da peça em Y=0
        vy = (max_y_px - pt[1]) / scale_factor
        
        final_vertices.append({'x': vx, 'y': vy})

    return final_vertices, None

# =============================================================================
# 3. GERAÇÃO DE G-CODE
# =============================================================================

def generateGcode(vertices: list, params: dict):
    """Gera a string final de G-code percorrendo a lista ordenada de vértices."""
    gcode_lines = []
    
    # Parâmetros com valores seguros padrão
    safe_z = params.get('safetyZ', 5.0)
    feed = params.get('feedRate', 300.0)
    spindle = params.get('spindleSpeed', 1200)
    # Profundidade deve ser negativa para cortar
    cut_depth = params.get('cutDepth', -1.0) 
    
    # Cabeçalho Padrão
    gcode_lines.append(f"({params.get('fileName', 'output.nc')})")
    gcode_lines.append(f"{params.get('units', 'G21')} ; Define milimetros")
    gcode_lines.append("G90 ; Coordenadas absolutas")
    gcode_lines.append("G17 ; Plano XY")
    gcode_lines.append(f"M03 S{spindle} ; Liga spindle")
    gcode_lines.append(f"G00 Z{safe_z} ; Z de seguranca")
    
    if not vertices:
        gcode_lines.append("(ERRO: Nenhum vértice processado)")
        return "\n".join(gcode_lines)

    # 1. Move para o primeiro ponto (início do corte)
    start_pt = vertices[0]
    gcode_lines.append(f"G00 X{start_pt['x']:.3f} Y{start_pt['y']:.3f}")
    
    # 2. Desce a ferramenta (Mergulho)
    # Nota: Feed de mergulho geralmente é menor (ex: 50% do feed de corte)
    gcode_lines.append(f"G01 Z{cut_depth} F{feed/2:.1f}")
    
    # 3. Percorre o contorno
    for point in vertices[1:]:
        gcode_lines.append(f"G01 X{point['x']:.3f} Y{point['y']:.3f} F{feed}")
        
    # 4. Fecha o contorno (Volta ao primeiro ponto)
    gcode_lines.append(f"G01 X{start_pt['x']:.3f} Y{start_pt['y']:.3f}")
    
    # Rodapé
    gcode_lines.append(f"G00 Z{safe_z} ; Sobe ferramenta")
    gcode_lines.append("M05 ; Desliga spindle")
    gcode_lines.append("M30 ; Fim de programa")
    
    return '\n'.join(gcode_lines)

# =============================================================================
# 4. ORQUESTRADOR (INTEGRAÇÃO)
# =============================================================================

def process_part_to_gcode(image_bytes: bytes, form_data: dict):
    
    # 1. Processamento de Imagem Robusto
    vertices, error = process_image_and_generate_geometry(image_bytes)
    
    if error:
        return f"Erro: {error}"
    
    # 2. Prepara Parâmetros
    thickness = float(form_data.get('thickness', 0)) # Se vier vazio, assume 0
    # Garante que cutDepth seja negativo e safetyZ positivo
    cut_depth = -abs(float(form_data.get('cutDepth', 1.0))) if float(form_data.get('cutDepth', 0)) != 0 else -1.0
    
    gcode_params = {
        'fileName': form_data.get('filename', 'peca.nc'),
        'units': form_data.get('units', 'G21'),
        'spindleSpeed': form_data.get('spindleSpeed', 1200),
        'safetyZ': float(form_data.get('safetyZ', 5.0)),
        'cutDepth': cut_depth,
        'feedRate': float(form_data.get('feedRate', 300))
    }

    # 3. Gera G-Code
    # Reutiliza sua função generateGcode existente, pois ela aceita a lista de dicts {'x', 'y'}
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

    gCode = process_part_to_gcode(image_bytes, params)

    # gcode_result = generateGcode(vertices, params)
    
    registerDatabase(params, gCode)
    
    return gCode

@app.get("/api/healthcheck", tags=["Health"])
def health_check():
    """Endpoint simples para verificar se a API está rodando."""
    # Rota de health check simples que retorna apenas a confirmação.
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
#         gcode = process_part_to_gcode(image_bytes, mock_form_data)
        
#         print("\n--- G-CODE GERADO ---\n")
#         print(gcode)
        
#         # Salva em arquivo
#         with open("output_final.nc", "w") as f:
#             f.write(gcode)
            
#     except FileNotFoundError:
#         print("Erro: Imagem de teste não encontrada.")