# Em backend/app/services/image_processor.py
import cv2
import numpy as np

def process_image_to_vertices(image_path: str):
    """
    Lê uma imagem, encontra o contorno principal e simplifica
    para uma lista de vértices.
    """
    
    # 1. Pré-processamento
    try:
        # Carrega a imagem em escala de cinza
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        
        # 1.3 Binarização: Transforma em preto e branco puro
        # O threshold (127) pode precisar de ajuste.
        # THRESH_BINARY_INV assume que a peça é clara e o fundo é escuro.
        _ , thresh = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
        
        # (Opcional) Limpar ruídos
        # thresh = cv2.medianBlur(thresh, 5)
        
    except Exception as e:
        print(f"Erro ao ler ou processar a imagem: {e}")
        return None

    # 2. Detecção de Contorno
    # Encontra todos os contornos na imagem
    # RETR_EXTERNAL pega apenas o contorno mais externo
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        print("Nenhum contorno encontrado.")
        return None

    # Pega o maior contorno (assumindo que seja a nossa peça)
    main_contour = max(contours, key=cv2.contourArea)

    # 3. Simplificação do Contorno
    # 'epsilon' é o parâmetro de precisão. 
    # Um valor maior = mais simples (menos vértices).
    # 1% do perímetro do contorno é um bom começo.
    epsilon = 0.01 * cv2.arcLength(main_contour, True)
    approx_vertices = cv2.approxPolyDP(main_contour, epsilon, True)

    # O formato de 'approx_vertices' é [[x,y]], [[x,y]], ...
    # Vamos simplificar para apenas [x,y], [x,y], ...
    # Também precisamos converter de pixels para mm (aqui, vamos supor 1 pixel = 1 mm)
    # No seu TCC, você pode ter um parâmetro de "escala" (pixels/mm)
    
    vertices_list = []
    for point in approx_vertices:
        x, y = point[0]
        # Invertendo Y, pois CV e CNC têm eixos Y opostos
        y = img.shape[0] - y 
        vertices_list.append({"x": float(x), "y": float(y)})

    print(f"Contorno simplificado para {len(vertices_list)} vértices.")
    
    # Esta lista de vértices é o seu "cvResults" para salvar no MongoDB
    # e passar para o gerador de G-code.
    return vertices_list

# -----------------------------------------------------------

# Em backend/app/services/gcode_generator.py
def generate_gcode_from_vertices(vertices: list, params: dict):
    """
    Recebe uma lista de vértices e os parâmetros do usuário
    e gera a string de G-code.
    """
    
    # Pega os parâmetros do formulário
    units = params.get('units', 'G21')
    speed = params.get('spindleSpeed', 1000)
    feed = params.get('feedRate', 500)
    safe_z = params.get('safetyZ', 5.0)
    cut_z = params.get('cutDepth', -1.0)
    
    gcode_lines = []
    
    # 1. Cabeçalho
    gcode_lines.append(f"({units} ; Unidades em mm)")
    gcode_lines.append("G90 ; Coordenadas absolutas")
    gcode_lines.append(f"M03 S{speed} ; Liga spindle")
    gcode_lines.append(f"G00 Z{safe_z} ; Move para Z de segurança")
    
    if not vertices:
        gcode_lines.append("(Nenhum vértice para processar)")
        return "\n".join(gcode_lines)

    # 2. Movimento inicial
    first_point = vertices[0]
    gcode_lines.append(f"G00 X{first_point['x']:.3f} Y{first_point['y']:.3f} ; Move para ponto inicial")
    
    # 3. Mergulho
    gcode_lines.append(f"G01 Z{cut_z} F{feed / 2} ; Mergulha na peça")
    
    # 4. Loop de Corte
    # Começa do *segundo* ponto, pois já estamos no primeiro
    for point in vertices[1:]:
        gcode_lines.append(f"G01 X{point['x']:.3f} Y{point['y']:.3f} F{feed}")
        
    # 5. Fechar o contorno
    gcode_lines.append(f"G01 X{first_point['x']:.3f} Y{first_point['y']:.3f} ; Fecha o contorno")
    
    # 6. Finalização
    gcode_lines.append(f"G00 Z{safe_z} ; Retrai ferramenta")
    gcode_lines.append("M05 ; Desliga spindle")
    gcode_lines.append("M30 ; Fim do programa")
    
    return "\n".join(gcode_lines)