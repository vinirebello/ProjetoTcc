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

def associate_measurements_to_lines(image_bytes: bytes):
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None: raise ValueError("Imagem inválida")
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Pré-processamento e Binarização
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # OCR
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
        d = pytesseract.image_to_data(thresh, config=custom_config, output_type=Output.DICT)
        
        measurements = []
        n_boxes = len(d['text'])
        for i in range(n_boxes):
            text = d['text'][i].strip()
            if text.isdigit():
                (x, y, w, h) = (d['left'][i], d['top'][i], d['width'][i], d['height'][i])
                measurements.append({
                    'value': int(text),
                    'box': (x, y, w, h),
                    'center': (x + w // 2, y + h // 2),
                    'associated_line': None
                })

        # Detecção de Linhas
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=40, maxLineGap=10)
        
        detected_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                detected_lines.append({
                    'coords': (x1, y1, x2, y2),
                    'midpoint': get_line_midpoint(x1, y1, x2, y2)
                })

        # Associação
        results = []
        for measure in measurements:
            min_dist = float('inf')
            best_line = None
            tx, ty = measure['center']
            
            for line in detected_lines:
                lx, ly = line['midpoint']
                dist = calculate_distance((tx, ty), (lx, ly))
                if dist < min_dist:
                    min_dist = dist
                    best_line = line
            
            if best_line:
                measure['associated_line'] = best_line['coords']
                measure['distance_to_line'] = min_dist
                results.append(measure)

        return results

    except Exception as e:
        print(f"Erro na visão computacional: {e}")
        return []

# =============================================================================
# 3. GERAÇÃO DE G-CODE
# =============================================================================

def generateGcode(vertices: list, params: dict):
    """Gera a string final de G-code com base nos vértices processados."""
    gcode_lines = []
    
    # Cabeçalho
    gcode_lines.append(f"({params.get('fileName', 'output.nc')})")
    gcode_lines.append(f"{params.get('units', 'G21')} ; Define unidades")
    gcode_lines.append("G90 ; Coordenadas absolutas")
    gcode_lines.append(f"M03 S{params.get('spindleSpeed', 1000)} ; Liga spindle")
    gcode_lines.append(f"G00 Z{params.get('safetyZ', 5.0)} ; Move para Z de segurança")
    
    if not vertices:
        gcode_lines.append("(Nenhum vértice válido encontrado)")
        return "\n".join(gcode_lines)

    # Movimento inicial
    first_point = vertices[0]
    gcode_lines.append(f"G00 X{first_point['x']:.3f} Y{first_point['y']:.3f}")
    
    # Mergulho (Aqui usamos a espessura como profundidade negativa)
    # Nota: O cutDepth deve ser negativo no G-Code para descer
    depth = params.get('cutDepth', -1.0)
    feed = float(params.get('feedRate', 100))
    gcode_lines.append(f"G01 Z{depth} F{feed / 2}")
    
    # Loop de Corte
    for point in vertices[1:]:
        gcode_lines.append(f"G01 X{point['x']:.3f} Y{point['y']:.3f} F{feed}")
        
    # Fechar o contorno (retorna ao primeiro ponto)
    gcode_lines.append(f"G01 X{first_point['x']:.3f} Y{first_point['y']:.3f}")
    
    # Finalização
    gcode_lines.append(f"G00 Z{params.get('safetyZ', 5.0)} ; Retrai ferramenta")
    gcode_lines.append("M05 ; Desliga spindle")
    gcode_lines.append("M30 ; Fim do programa")
    
    return '\n'.join(gcode_lines)

# =============================================================================
# 4. ORQUESTRADOR (INTEGRAÇÃO)
# =============================================================================

def process_part_to_gcode(image_bytes: bytes, form_data: dict):
    """
    Função principal que recebe a imagem e os dados do formulário (React/Frontend),
    processa a imagem, converte escalas e gera o G-Code.
    """
    
    # 1. Executa a Visão Computacional
    extracted_data = associate_measurements_to_lines(image_bytes)
    
    if not extracted_data:
        return "Erro: Nenhuma cota ou linha detectada. Verifique a qualidade da imagem."

    # 2. Calcula o Fator de Escala (Pixels -> mm)
    # O OCR nos dá o valor real (ex: 100mm). A linha tem comprimento em pixels (ex: 500px).
    # Fator = pixels / valor_real.
    scale_factors = []
    
    print("\n--- Analisando Escalas ---")
    for item in extracted_data:
        x1, y1, x2, y2 = item['associated_line']
        pixel_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        real_value = item['value'] # Valor lido pelo OCR
        
        if real_value > 0:
            ratio = pixel_length / real_value
            scale_factors.append(ratio)
            print(f"Cota: {real_value} | Pixels: {pixel_length:.2f} | Ratio: {ratio:.2f} px/unidade")

    # Média dos fatores para ter uma escala global mais precisa
    if not scale_factors:
        return "Erro: Não foi possível determinar a escala da imagem."
    
    global_scale = sum(scale_factors) / len(scale_factors)
    print(f"Escala Global Usada: {global_scale:.4f} pixels por unidade")

    # 3. Converte Coordenadas e Cria Vértices
    # IMPORTANTE: O gerador de G-Code espera uma lista ordenada de vértices.
    # O OCR retorna linhas soltas. Aqui vamos simplificar e pegar os pontos das linhas detectadas.
    vertices = []
    
    # Offset para zerar a peça (trazer para o 0,0)
    # Pegamos o menor X e Y detectados
    min_x = float('inf')
    min_y = float('inf')
    
    temp_points = []
    for item in extracted_data:
        coords = item['associated_line'] # (x1, y1, x2, y2)
        temp_points.append((coords[0], coords[1]))
        temp_points.append((coords[2], coords[3]))
        
        min_x = min(min_x, coords[0], coords[2])
        min_y = min(min_y, coords[1], coords[3])

    # Preenchendo os vértices convertidos e normalizados
    # Nota: Em OpenCV o Y cresce para baixo, em CNC cresce para cima. 
    # Muitas vezes é necessário inverter o Y, mas aqui manteremos o padrão da imagem.
    for px, py in temp_points:
        vertex = {
            'x': (px - min_x) / global_scale, # Converte para mm e zera eixo
            'y': (py - min_y) / global_scale  # Converte para mm e zera eixo
        }
        # Evita duplicar pontos muito próximos (opcional, mas bom para limpeza)
        vertices.append(vertex)

    # 4. Prepara Parâmetros para o Gerador
    # A espessura vem do formulário do front
    thickness = float(form_data.get('thickness', 0)) 
    
    gcode_params = {
        'fileName': form_data.get('filename', 'peca_output.nc'),
        'units': 'G21', # mm
        'spindleSpeed': form_data.get('spindle', 1200),
        'safetyZ': 5.0,
        'cutDepth': -abs(thickness), # Garante que seja negativo para cortar
        'feedRate': form_data.get('feedrate', 300)
    }

    # 5. Gera o arquivo final
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