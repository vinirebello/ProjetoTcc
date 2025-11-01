import cv2
import numpy as np

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
    
    return "\n".join(gcode_lines)


IMAGE_PATH = "image3.png"  # 1. Troque pelo nome do seu arquivo de imagem

# 2. Carrega a imagem do disco e converte para bytes
try:
    with open(IMAGE_PATH, 'rb') as f:
        image_data_bytes = f.read()
except FileNotFoundError:
    print(f"ERRO: O arquivo de imagem '{IMAGE_PATH}' não foi encontrado.")
    print("Certifique-se de que a imagem está na mesma pasta que o script.")
    exit()

# 3. Chama a função de teste
print(f"Processando a imagem: {IMAGE_PATH}")
vertices = process_image_to_vertices(image_data_bytes)

# 4. Exibe o resultado
if vertices is not None:
    print("\n✅ Vértices Encontrados:")
    for vertex in vertices:
        # Formatação para melhor visualização
        print(f"  X: {vertex['x']:.2f}, Y: {vertex['y']:.2f}")
    
    print(f"\nTotal de vértices: {len(vertices)}")
else:
    print("\n❌ Não foi possível extrair os vértices ou nenhum contorno foi encontrado.")