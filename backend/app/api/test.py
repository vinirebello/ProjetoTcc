import cv2
import numpy as np
import pytesseract

import cv2
import numpy as np
import pytesseract
from scipy.spatial import point_to_segment_distance

# Configuração do caminho do Tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def analyze_complex_drawing_dimensions(image_bytes: bytes):
    """
    Analisa um desenho 2D de peça simples (como um L), extraindo vértices,
    cotas com localização e associando as cotas às linhas da peça.
    """
    results = {
        "vertices": [],
        "lines": [],
        "dimensions": []
    }

    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_color = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        img_gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)

        if img_color is None or img_gray is None:
            raise ValueError("Não foi possível decodificar a imagem.")

        img_height, img_width = img_gray.shape[:2]

        # --- 1. Extração do Contorno Principal e Vértices ---
        _, thresh_contour = cv2.threshold(img_gray, 127, 255, cv2.THRESH_BINARY_INV) 
        # Invertemos para ter o objeto (preto) em branco e o fundo em preto,
        # o que ajuda o findContours a encontrar o "objeto"
        
        contours, _ = cv2.findContours(thresh_contour, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return results

        main_contour = max(contours, key=cv2.contourArea)
        
        # Simplifica o contorno para obter os vértices da forma
        epsilon = 0.01 * cv2.arcLength(main_contour, True) # Ajuste este valor se necessário
        approx_vertices_cv = cv2.approxPolyDP(main_contour, epsilon, True)
        
        # Converte vértices para formato desejado (x, y) e inverte Y para sistema CNC
        vertices_coords = []
        for point in approx_vertices_cv:
            x, y = point[0]
            y_cnc = img_height - y  # Inverte o eixo Y
            vertices_coords.append((float(x), float(y_cnc)))
            results["vertices"].append({"x": float(x), "y": float(y_cnc)})

        # --- 2. Identificação das Linhas da Peça ---
        # Cria segmentos de linha conectando os vértices em ordem
        lines = []
        for i in range(len(vertices_coords)):
            p1 = vertices_coords[i]
            p2 = vertices_coords[(i + 1) % len(vertices_coords)] # Conecta o último ao primeiro
            
            # Calcula o ponto médio da linha para futura associação
            mid_x = (p1[0] + p2[0]) / 2
            mid_y = (p1[1] + p2[1]) / 2
            
            # Determina a orientação da linha
            if abs(p1[0] - p2[0]) < 5: # Tolerância para considerar vertical (quase mesma coordenada X)
                orientation = "vertical"
            elif abs(p1[1] - p2[1]) < 5: # Tolerância para considerar horizontal (quase mesma coordenada Y)
                orientation = "horizontal"
            else:
                orientation = "diagonal" # Linhas diagonais não são esperadas neste tipo de desenho simples

            lines.append({
                "p1": {"x": p1[0], "y": p1[1]},
                "p2": {"x": p2[0], "y": p2[1]},
                "midpoint": {"x": mid_x, "y": mid_y},
                "orientation": orientation,
                "length_px": np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            })
        results["lines"] = lines


        # --- 3. Extração de Cotas com OCR (incluindo localização) ---
        inverted_ocr = cv2.bitwise_not(img_gray)
        _, thresh_ocr = cv2.threshold(inverted_ocr, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
        data = pytesseract.image_to_data(thresh_ocr, output_type=pytesseract.Output.DICT, config=custom_config, lang='eng')

        # --- 4. Associação das Cotas às Linhas ---
        for i in range(len(data['text'])):
            text_value = data['text'][i].strip()
            
            # Filtra para manter apenas números com boa confiança
            if text_value.isdigit() and int(data['conf'][i]) > 70: # Aumenta a confiança para ser mais seletivo
                x_text, y_text, w_text, h_text = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                
                # Centro da caixa de texto (em coordenadas de imagem, não CNC)
                cx_text = x_text + w_text / 2
                cy_text = y_text + h_text / 2
                
                # Determina a orientação aproximada da cota (horizontal ou vertical)
                # Assume que a cota é horizontal se a largura da caixa de texto for maior que a altura
                # E vertical se a altura for maior que a largura
                if w_text > h_text * 1.5: # Cota horizontal
                    cota_orientation = "horizontal"
                elif h_text > w_text * 1.5: # Cota vertical
                    cota_orientation = "vertical"
                else:
                    continue # Ignora cotas com proporções ambíguas (pode ser ruído)
                
                min_distance = float('inf')
                associated_line_index = -1
                
                # Itera sobre as linhas da peça para encontrar a mais próxima e com a mesma orientação
                for j, line in enumerate(lines):
                    if line["orientation"] == cota_orientation:
                        # Ponto da cota para cálculo de distância
                        # Para cotas horizontais, usamos o centro X e Y da caixa de texto.
                        # Para cotas verticais, usamos o centro X e Y da caixa de texto.
                        # As linhas estão em coordenadas CNC (Y invertido), então precisamos converter cy_text
                        
                        # Converte cy_text para coordenadas CNC para comparação
                        cy_text_cnc = img_height - cy_text
                        
                        # Pontos da linha (em coordenadas CNC)
                        p1_line_cnc = (line["p1"]["x"], line["p1"]["y"])
                        p2_line_cnc = (line["p2"]["x"], line["p2"]["y"])
                        
                        # Calcula a distância do centro da cota (ponto) ao segmento de linha
                        # from scipy.spatial.distance.point_to_segment_distance
                        # Requer que os pontos sejam arrays numpy
                        distance = point_to_segment_distance(
                            np.array([cx_text, cy_text_cnc]),
                            np.array([p1_line_cnc[0], p1_line_cnc[1]]),
                            np.array([p2_line_cnc[0], p2_line_cnc[1]])
                        )
                        
                        # Verifica se a cota está "do lado de fora" da peça em relação à linha
                        # Isso é um pouco mais complexo e pode exigir um cálculo de vetor normal ou
                        # uma verificação de posição relativa. Para simplificar, assumimos que 
                        # as cotas geralmente estão fora da peça.

                        if distance < min_distance:
                            min_distance = distance
                            associated_line_index = j
                
                # Se uma linha foi associada e a distância é razoável
                if associated_line_index != -1 and min_distance < 80: # 80 pixels de tolerância
                    associated_line = lines[associated_line_index]
                    results["dimensions"].append({
                        "value": text_value,
                        "associated_line_index": associated_line_index,
                        "associated_line": {
                            "p1": associated_line["p1"],
                            "p2": associated_line["p2"],
                            "orientation": associated_line["orientation"],
                            "length_px_approx": associated_line["length_px"] # Comprimento aproximado em pixels
                        },
                        "position_box_img_coords": {"x": x_text, "y": y_text, "w": w_text, "h": h_text},
                        "distance_to_line_px": min_distance
                    })

    except Exception as e:
        print(f"Erro na análise do desenho: {e}")
        return None
        
    return results

# --- Exemplo de Uso (adaptado para a nova imagem) ---
if __name__ == "__main__":
    # Carregue a imagem (certifique-se de que o nome do arquivo está correto)
    # Por exemplo, se você salvou a imagem como 'peca_em_l.png'
    try:
        with open('peca_em_l.png', 'rb') as f:
            image_data_l_shape = f.read()
        
        analysis_results = analyze_complex_drawing_dimensions(image_data_l_shape)
        
        if analysis_results:
            print("\n--- RESULTADOS DA ANÁLISE DO DESENHO ---")
            
            print("\nVértices da Peça (CNC/Invertido Y):")
            for i, v in enumerate(analysis_results["vertices"]):
                print(f"  Vértice {i}: ({v['x']:.2f}, {v['y']:.2f})")
                
            print("\nLinhas da Peça:")
            for i, line in enumerate(analysis_results["lines"]):
                print(f"  Linha {i}: P1=({line['p1']['x']:.2f},{line['p1']['y']:.2f}), P2=({line['p2']['x']:.2f},{line['p2']['y']:.2f})")
                print(f"    Orientação: {line['orientation']}, Comprimento (px): {line['length_px']:.2f}")
                
            print("\nDimensões Associadas:")
            for dim in analysis_results["dimensions"]:
                print(f"  Valor: {dim['value']}")
                print(f"    Associada à Linha Index: {dim['associated_line_index']}")
                print(f"    Linha: P1=({dim['associated_line']['p1']['x']:.2f},{dim['associated_line']['p1']['y']:.2f}), P2=({dim['associated_line']['p2']['x']:.2f},{dim['associated_line']['p2']['y']:.2f})")
                print(f"    Orientação da Linha: {dim['associated_line']['orientation']}")
                print(f"    Distância à Linha (px): {dim['distance_to_line_px']:.2f}")
                print(f"    Bounding Box (imagem): {dim['position_box_img_coords']}")
        else:
            print("Não foi possível analisar o desenho.")
            
    except FileNotFoundError:
        print("Erro: O arquivo de imagem não foi encontrado. Certifique-se de que 'peca_em_l.png' está no mesmo diretório.")
    except Exception as e:
        print(f"Erro geral durante a execução: {e}")

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
        # _, thresh = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        
        # 3. Aplicação do OCR (Tesseract)
        # Configuração para números (digitos) e para otimizar a leitura
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
        
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        
        # Extrai o texto da imagem processada
        text = pytesseract.image_to_string(thresh, config=custom_config, lang='eng') # 'eng' geralmente funciona bem para números simples

        # 4. Limpeza e Extração dos Números
        # Remove caracteres de quebra de linha ou espaços indesejados e separa os números
        numbers = [s.strip() for s in text.split() if s.isdigit()]
        
        return list(numbers) # Retorna valores únicos (como "200")

    except Exception as e:
        print(f"Erro na extração de medidas: {e}")
        return []

IMAGE_PATH = "imagetest.png"  # 1. Troque pelo nome do seu arquivo de imagem

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
# vertices = process_image_to_vertices(image_data_bytes)

medidas = extract_measurements(image_data_bytes)

result = analyze_complex_drawing_dimensions(image_data_bytes)

# print(medidas)
print(result)

# 4. Exibe o resultado
# if vertices is not None:
#     print("\n✅ Vértices Encontrados:")
#     for vertex in vertices:
#         # Formatação para melhor visualização
#         print(f"  X: {vertex['x']:.2f}, Y: {vertex['y']:.2f}")
    
#     print(f"\nTotal de vértices: {len(vertices)}")
# else:
#     print("\n❌ Não foi possível extrair os vértices ou nenhum contorno foi encontrado.")