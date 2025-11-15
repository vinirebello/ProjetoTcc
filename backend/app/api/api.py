import cv2
import numpy as np
import uvicorn
import pytesseract
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import registerDatabase
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



def extractVertices(image_bytes: bytes):
    """
    Lê uma imagem, encontra o contorno principal e simplifica
    para uma lista de vértices.
    """
    try:
        
        nparr = np.frombuffer(image_bytes, np.uint8)  
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        
        if img is None:
            raise ValueError("Não foi possível decodificar a imagem.")
        
        _ , thresh = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
        
    except Exception as e:
        print(f"Erro no pré-processamento: {e}")
        return None

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None

    main_contour = max(contours, key=cv2.contourArea)
    epsilon = 0.01 * cv2.arcLength(main_contour, True)
    approx_vertices = cv2.approxPolyDP(main_contour, epsilon, True)

    vertices_list = []
    img_height = img.shape[0]
    for point in approx_vertices:
        
        x, y = point[0]  
        y_cnc = img_height - y 
        vertices_list.append({"x": float(x), "y": float(y_cnc)})
    
    return vertices_list

def extract_measurements(image_bytes: bytes):
    """
    Lê uma imagem, pré-processa e usa OCR para extrair texto (medidas).
    """
    try:
        # 1. Decodificação e Conversão
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_original = cv2.imdecode(nparr, cv2.IMREAD_COLOR) # Use COLOR para melhor OCR
        
        if img_original is None:
            raise ValueError("Não foi possível decodificar a imagem.")
            
        # 2. Pré-processamento para OCR
        gray = cv2.cvtColor(img_original, cv2.COLOR_BGR2GRAY)
        
        # O desenho da sua imagem é preto em fundo branco. 
        # Inverter cores pode ajudar o Tesseract a tratar o texto como preto sobre branco.
        inverted = cv2.bitwise_not(gray) 
        
        # Binarização (Limiarização)
        _, thresh = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        
        # 3. Aplicação do OCR (Tesseract)
        # Configuração para números (digitos) e para otimizar a leitura
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
        
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        
        # Extrai o texto da imagem processada
        text = pytesseract.image_to_string(thresh, config=custom_config, lang='eng') # 'eng' geralmente funciona bem para números simples

        # 4. Limpeza e Extração dos Números
        # Remove caracteres de quebra de linha ou espaços indesejados e separa os números
        numbers = [s.strip() for s in text.split() if s.isdigit()]
        
        return list(set(numbers)) # Retorna valores únicos (como "200")

    except Exception as e:
        print(f"Erro na extração de medidas: {e}")
        return []

def generateGcode(vertices: list, params: dict):
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
    
    file: UploadFile = File(...), 
    units: str = Form(...),
    spindleSpeed: int = Form(...),
    feedRate: float = Form(...),
    safetyZ: float = Form(...),
    cutDepth: float = Form(...)):
    
    image_bytes = await file.read()
    
    vertices = extractVertices(image_bytes)
    
    if vertices is None:
        raise HTTPException(status_code=400, detail="Não foi possível processar a imagem. Verifique se é uma silhueta P&B.")

    params = {
        "fileName": file.filename,
        "units": units,
        "spindleSpeed": spindleSpeed,
        "feedRate": feedRate,
        "safetyZ": safetyZ,
        "cutDepth": cutDepth
    }

    gcode_result = generateGcode(vertices, params)
    
    registerDatabase(params, gcode_result)
    
    return gcode_result

@app.get("/api/healthcheck", tags=["Health"])
def health_check():
    """Endpoint simples para verificar se a API está rodando."""
    # Rota de health check simples que retorna apenas a confirmação.
    return "API Ativa!"

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
