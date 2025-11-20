import cv2
import numpy as np
import pytesseract
from pytesseract import Output
import math

# Configure o caminho do tesseract se necessário
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def calculate_distance(p1, p2):
    """Calcula a distância euclidiana entre dois pontos (x,y)."""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def get_line_midpoint(x1, y1, x2, y2):
    """Retorna o ponto central de uma linha."""
    return ((x1 + x2) // 2, (y1 + y2) // 2)

def associate_measurements_to_lines(image_bytes: bytes):
    try:
        # 1. Carregamento e Pré-processamento
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None: raise ValueError("Imagem inválida")
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Binarização para o OCR (Preto e Branco)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 2. Extração de Texto com Coordenadas (OCR)
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
        d = pytesseract.image_to_data(thresh, config=custom_config, output_type=Output.DICT)
        
        measurements = []
        n_boxes = len(d['text'])
        
        for i in range(n_boxes):
            text = d['text'][i].strip()
            if text.isdigit(): # Filtra apenas o que for número
                (x, y, w, h) = (d['left'][i], d['top'][i], d['width'][i], d['height'][i])
                # Calcula o centro da caixa de texto
                center_text = (x + w // 2, y + h // 2)
                measurements.append({
                    'value': int(text),
                    'box': (x, y, w, h),
                    'center': center_text,
                    'associated_line': None
                })

        # 3. Detecção de Linhas (Canny + HoughLinesP)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # minLineLength alto ajuda a ignorar os traços dos próprios números
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=40, maxLineGap=10)
        
        detected_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                detected_lines.append({
                    'coords': (x1, y1, x2, y2),
                    'midpoint': get_line_midpoint(x1, y1, x2, y2)
                })

        # 4. Algoritmo de Associação (Texto -> Linha mais próxima)
        # Para cada cota encontrada, procuramos a linha cujo ponto central está mais próximo
        results = []
        
        img_debug = img.copy() # Para visualização
        
        for measure in measurements:
            min_dist = float('inf')
            best_line = None
            
            tx, ty = measure['center']
            
            for line in detected_lines:
                lx, ly = line['midpoint']
                dist = calculate_distance((tx, ty), (lx, ly))
                
                # Threshold de distância (opcional): se estiver muito longe, ignora
                if dist < min_dist:
                    min_dist = dist
                    best_line = line
            
            if best_line:
                measure['associated_line'] = best_line['coords']
                measure['distance_to_line'] = min_dist
                results.append(measure)

                # --- DESENHO DE DEBUG (OPCIONAL) ---
                # Desenha retângulo no texto
                cv2.rectangle(img_debug, (measure['box'][0], measure['box'][1]), 
                              (measure['box'][0] + measure['box'][2], measure['box'][1] + measure['box'][3]), (0, 255, 0), 2)
                # Desenha a linha associada
                l = best_line['coords']
                cv2.line(img_debug, (l[0], l[1]), (l[2], l[3]), (0, 0, 255), 3)
                # Desenha conexão visual
                cv2.line(img_debug, measure['center'], best_line['midpoint'], (255, 0, 0), 1)
            
        # Salvar imagem de debug para você ver o resultado visualmente
        cv2.imwrite("debug_association.png", img_debug)
        
        return results

    except Exception as e:
        print(f"Erro: {e}")
        return []

# --- Execução ---
try:
    with open("imagetest.png", "rb") as f:
        image_bytes = f.read()
    
    data = associate_measurements_to_lines(image_bytes)
    
    # Exibindo resultado estruturado
    print(f"{'COTA':<10} | {'COORDENADAS DA LINHA (x1,y1,x2,y2)':<30} | {'DISTÂNCIA'}")
    print("-" * 60)
    for item in data:
        print(f"{item['value']:<10} | {str(item['associated_line']):<30} | {item['distance_to_line']:.2f}")
        
except FileNotFoundError:
    print("Arquivo não encontrado.")