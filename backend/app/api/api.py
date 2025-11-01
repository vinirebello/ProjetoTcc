import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import io

# --- 1. Configuração do App FastAPI ---
app = FastAPI()

# Configura o CORS para permitir que o seu frontend React (ex: localhost:3000)
# se comunique com o seu backend (ex: localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Em produção, mude para ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. Lógica de Visão Computacional (OpenCV) ---
# (Como discutido anteriormente)
def process_image_to_vertices(image_bytes: bytes):
    """
    Lê uma imagem, encontra o contorno principal e simplifica
    para uma lista de vértices.
    """
    try:
        # Converte os bytes da imagem em um array numpy
        nparr = np.frombuffer(image_bytes, np.uint8)
        # Decodifica a imagem em escala de cinza
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        
        if img is None:
            raise ValueError("Não foi possível decodificar a imagem.")
        
        # Binarização (Thresholding)
        # Assume peça clara (branco) em fundo escuro (preto)
        _ , thresh = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
        
    except Exception as e:
        print(f"Erro no pré-processamento: {e}")
        return None

    # Detecção de Contorno
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None

    main_contour = max(contours, key=cv2.contourArea)

    # Simplificação do Contorno (Algoritmo Ramer-Douglas-Peucker)
    epsilon = 0.01 * cv2.arcLength(main_contour, True)
    approx_vertices = cv2.approxPolyDP(main_contour, epsilon, True)

    vertices_list = []
    img_height = img.shape[0]
    for point in approx_vertices:
        x, y = point[0]
        # Invertendo Y, pois CV e CNC têm eixos Y opostos
        y_cnc = img_height - y 
        # ASSUMINDO 1 pixel = 1 mm (ou unidade)
        vertices_list.append({"x": float(x), "y": float(y_cnc)})
    
    return vertices_list

# --- 3. Lógica de Geração de G-code ---
def generate_gcode_from_vertices(vertices: list, params: dict):
    """
    Recebe vértices e parâmetros e gera a string de G-code.
    """
    gcode_lines = []
    
    # 1. Cabeçalho
    gcode_lines.append(f"({params['fileName']})")
    gcode_lines.append(f"{params['units']} ; Define unidades")
    gcode_lines.append("G90 ; Coordenadas absolutas")
    gcode_lines.append(f"M03 S{params['spindleSpeed']} ; Liga spindle")
    gcode_lines.append(f"G00 Z{params['safetyZ']} ; Move para Z de segurança")
    
    if not vertices:
        gcode_lines.append("(Nenhum vértice encontrado)")
        return "\n".join(gcode_lines)

    # 2. Movimento inicial
    first_point = vertices[0]
    gcode_lines.append(f"G00 X{first_point['x']:.3f} Y{first_point['y']:.3f}")
    
    # 3. Mergulho
    gcode_lines.append(f"G01 Z{params['cutDepth']} F{float(params['feedRate']) / 2}")
    
    # 4. Loop de Corte
    for point in vertices[1:]:
        gcode_lines.append(f"G01 X{point['x']:.3f} Y{point['y']:.3f} F{params['feedRate']}")
        
    # 5. Fechar o contorno
    gcode_lines.append(f"G01 X{first_point['x']:.3f} Y{first_point['y']:.3f}")
    
    # 6. Finalização
    gcode_lines.append(f"G00 Z{params['safetyZ']} ; Retrai ferramenta")
    gcode_lines.append("M05 ; Desliga spindle")
    gcode_lines.append("M30 ; Fim do programa")
    
    finalGcode = '\n'.join(gcode_lines)
    
    print(finalGcode)
    
    return finalGcode.strip()

# --- 4. O Endpoint da API ---
@app.post("/api/generate-gcode")
async def create_gcode(
    # 'File' vem do <input type="file">
    file: UploadFile = File(...), 
    
    # 'Form' vem dos seus inputs de formulário
    units: str = Form(...),
    spindleSpeed: int = Form(...),
    feedRate: float = Form(...),
    safetyZ: float = Form(...),
    cutDepth: float = Form(...)):
    
    # Lê os bytes do arquivo enviado
    image_bytes = await file.read()
    
    # 1. Processa a imagem com OpenCV
    vertices = process_image_to_vertices(image_bytes)
    
    if vertices is None:
        raise HTTPException(status_code=400, detail="Não foi possível processar a imagem. Verifique se é uma silhueta P&B.")

    # 2. Coleta os parâmetros
    params = {
        "fileName": file.filename,
        "units": units,
        "spindleSpeed": spindleSpeed,
        "feedRate": feedRate,
        "safetyZ": safetyZ,
        "cutDepth": cutDepth
    }

    # 3. Gera o G-code
    gcode_result = generate_gcode_from_vertices(vertices, params)
    
    # 4. Retorna o G-code como texto puro
    return gcode_result

# --- 5. Roda o servidor ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
