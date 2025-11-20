import cv2
import numpy as np
import pytesseract
import typing
import os # Usado para ler os arquivos

# ==============================================================================
# 1. FUNÇÕES DE GERAÇÃO DE G-CODE (Originais e Modificadas)
# ==============================================================================

def extract_measurements(image_bytes: bytes):
    """
    Lê uma imagem, pré-processa e usa OCR para extrair texto (medidas).
    Esta versão é usada para a 'vista de perfil' (só precisamos dos números).
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_original = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_original is None:
            raise ValueError("Não foi possível decodificar a imagem.")
            
        gray = cv2.cvtColor(img_original, cv2.COLOR_BGR2GRAY)
        
        # Inverter cores (assumindo texto preto em fundo branco)
        inverted = cv2.bitwise_not(gray) 
        
        # Binarização
        _, thresh = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        
        # Config Tesseract
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
        
        # !! IMPORTANTE: Configure o caminho do Tesseract aqui !!
        # pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        
        text = pytesseract.image_to_string(thresh, config=custom_config, lang='eng')

        numbers = [s.strip() for s in text.split() if s.isdigit()]
        
        return list(numbers)

    except Exception as e:
        print(f"Erro na extração de medidas: {e}")
        return []

def extract_dimension_data(image_bytes: bytes):
    """
    Extrai dados das cotas (texto e posição) usando Tesseract.
    Usado para a 'vista de topo' para encontrar a escala.
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_original = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_original is None:
            raise ValueError("Não foi possível decodificar a imagem.")
            
        gray = cv2.cvtColor(img_original, cv2.COLOR_BGR2GRAY)
        inverted = cv2.bitwise_not(gray) 
        _, thresh = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        
        # !! IMPORTANTE: Configure o caminho do Tesseract aqui !!
        # pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
        
        # Mude para image_to_data e peça um dicionário (Output.DICT)
        data = pytesseract.image_to_data(thresh, config=custom_config, lang='eng', output_type=pytesseract.Output.DICT)
        
        extracted_data = []
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > 70 and data['text'][i].isdigit():
                extracted_data.append({
                    "text": data['text'][i],
                    "left": data['left'][i],
                    "top": data['top'][i],
                    "width": data['width'][i],
                    "height": data['height'][i]
                })
        return extracted_data

    except Exception as e:
        print(f"Erro na extração de dados de medidas: {e}")
        return []

def process_image_to_scaled_vertices(image_bytes: bytes, scale_factor: float) -> typing.Tuple[typing.List[dict], dict]:
    """
    Lê uma imagem, encontra o contorno principal, simplifica
    e APLICA A ESCALA para uma lista de vértices em mm.
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError("Não foi possível decodificar a imagem.")
        
        # Binarização
        # !! MODIFICAÇÃO !!
        # THRESH_BINARY_INV é usado se o seu desenho for linhas PRETAS em fundo BRANCO.
        # Use THRESH_BINARY se for linhas BRANCAS em fundo PRETO.
        _ , thresh = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV) 
        
    except Exception as e:
        print(f"Erro no pré-processamento: {e}")
        return None, None

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None, None

    main_contour = max(contours, key=cv2.contourArea)

    # Obter a caixa delimitadora em pixels
    x_px, y_px, w_px, h_px = cv2.boundingRect(main_contour)
    pixel_bbox = {"w_px": w_px, "h_px": h_px}
    
    # Simplificação do Contorno
    epsilon = 0.01 * cv2.arcLength(main_contour, True)
    approx_vertices = cv2.approxPolyDP(main_contour, epsilon, True)

    vertices_list = []
    img_height = img.shape[0]
    
    # Encontrar o ponto de origem (menor X e menor Y) para "zerar" a peça
    # Isso garante que o G-code comece próximo de (0,0)
    min_x_px = min(p[0][0] for p in approx_vertices)
    min_y_px = min(p[0][1] for p in approx_vertices)

    for point in approx_vertices:
        x, y = point[0]
        
        # Normaliza para a origem da peça
        x_norm = x - min_x_px
        y_norm = y - min_y_px
        
        # Invertendo Y (CV vs CNC) e normalizando
        # (img_height - y) inverte. (img_height - min_y_px) é o novo "chão".
        y_cnc = (img_height - y) - (img_height - min_y_px)
        # O resultado acima simplifica para:
        y_cnc = min_y_px - y
        # Mas se o contorno já foi simplificado, o mais seguro é:
        # Achar o Y máximo (que é o 'min_y' em coordenadas CNC)
        max_y_cnc_coord = img_height - min_y_px
        y_cnc = (img_height - y) - max_y_cnc_coord
        
        # Simplificação: vamos usar a lógica original, mas normalizada
        # A sua lógica original estava correta, mas vamos aplicar o scale_factor
        
        x_original, y_original = point[0]
        y_cnc_original = img_height - y_original # Y invertido
        
        # APLICA A ESCALA
        x_scaled = float(x_original) * scale_factor
        y_scaled = float(y_cnc_original) * scale_factor
        
        vertices_list.append({"x": x_scaled, "y": y_scaled})

    # Re-centralizar os vértices escalados na origem (0,0)
    if vertices_list:
        min_x_scaled = min(v['x'] for v in vertices_list)
        min_y_scaled = min(v['y'] for v in vertices_list)
        
        for v in vertices_list:
            v['x'] -= min_x_scaled
            v['y'] -= min_y_scaled
            
    return vertices_list, pixel_bbox


def generate_gcode_from_vertices(vertices: list, params: dict) -> str:
    """
    Recebe vértices e parâmetros e gera a string de G-code.
    (Sua função original)
    """
    gcode_lines = []
    
    # 1. Cabeçalho
    gcode_lines.append(f"({params['fileName']})")
    gcode_lines.append(f"{params['units']} ; Define unidades")
    gcode_lines.append("G90 ; Coordenadas absolutas")
    gcode_lines.append(f"M03 S{params['spindleSpeed']} ; Liga spindle")
    gcode_lines.append(f"G00 Z{params['safetyZ']:.3f} ; Move para Z de segurança")
    
    if not vertices:
        gcode_lines.append("(Nenhum vértice encontrado)")
        return "\n".join(gcode_lines)

    # 2. Movimento inicial
    first_point = vertices[0]
    gcode_lines.append(f"G00 X{first_point['x']:.3f} Y{first_point['y']:.3f}")
    
    # 3. Mergulho
    gcode_lines.append(f"G01 Z{params['cutDepth']:.3f} F{float(params['feedRate']) / 2}")
    
    # 4. Loop de Corte (Garante que o primeiro ponto seja o destino final)
    path_vertices = vertices[1:] + [first_point]
    
    for point in path_vertices:
        gcode_lines.append(f"G01 X{point['x']:.3f} Y{point['y']:.3f} F{params['feedRate']}")
        
    # 6. Finalização
    gcode_lines.append(f"G00 Z{params['safetyZ']:.3f} ; Retrai ferramenta")
    gcode_lines.append("M05 ; Desliga spindle")
    gcode_lines.append("M30 ; Fim do programa")
    
    return "\n".join(gcode_lines)

# ==============================================================================
# 2. FUNÇÃO PRINCIPAL (ORQUESTRADOR)
# ==============================================================================

def process_and_generate_gcode(top_view_bytes: bytes, profile_view_bytes: bytes, base_params: dict) -> str:
    """
    Orquestra o processo completo:
    1. Pega a profundidade (Z) da imagem de perfil.
    2. Pega a escala (mm/px) da imagem de topo.
    3. Processa os vértices (X,Y) da imagem de topo com a escala.
    4. Gera o G-code final.
    """
    
    # --- Passo 1: Processar Imagem de Perfil (Obter Z) ---
    print("[LOG] Processando imagem de perfil para profundidade (Z)...")
    profile_dims = extract_measurements(profile_view_bytes)
    if not profile_dims:
        raise ValueError("Nenhuma cota encontrada na imagem de perfil.")
    
    # Assume a primeira (ou maior) dimensão como profundidade
    cut_depth_value = float(sorted(profile_dims, key=float, reverse=True)[0])
    base_params['cutDepth'] = -abs(cut_depth_value)
    print(f"[LOG] Profundidade (Z) definida para: {base_params['cutDepth']} mm")

    # --- Passo 2: Processar Imagem de Topo (Obter Escala) ---
    print("[LOG] Processando imagem de topo para escala (X, Y)...")
    dimension_data = extract_dimension_data(top_view_bytes)
    if not dimension_data:
        raise ValueError("Nenhuma cota legível encontrada na imagem de topo.")
    
    # Assume a maior dimensão de texto encontrada é a dimensão principal
    real_dims = sorted([float(d['text']) for d in dimension_data], reverse=True)
    main_real_dimension = real_dims[0] # Ex: 400.0 (em mm)
    
    # --- Passo 3: Obter Dimensões em Pixel ---
    # Processa uma vez com escala 1.0 apenas para pegar o 'pixel_bbox'
    _, pixel_bbox = process_image_to_scaled_vertices(top_view_bytes, scale_factor=1.0)
    if not pixel_bbox:
        raise ValueError("Nenhum contorno encontrado na imagem de topo.")
        
    # Assume que a dimensão principal real corresponde ao maior lado em pixels
    main_pixel_dimension = max(pixel_bbox['w_px'], pixel_bbox['h_px'])
    
    # --- Passo 4: Calcular Fator de Escala ---
    if main_pixel_dimension == 0:
        raise ValueError("Dimensão em pixel é zero.")
    
    scale_factor = main_real_dimension / main_pixel_dimension
    
    print(f"[LOG] Dimensão Real (Topo): {main_real_dimension} mm")
    print(f"[LOG] Dimensão Pixel (Topo): {main_pixel_dimension} px")
    print(f"[LOG] Fator de Escala: {scale_factor:.4f} mm/pixel")

    # --- Passo 5: Processar Vértices com a Escala Correta ---
    scaled_vertices, _ = process_image_to_scaled_vertices(top_view_bytes, scale_factor=scale_factor)
    
    if not scaled_vertices:
        raise ValueError("Falha ao processar vértices escalados.")
    
    print(f"[LOG] {len(scaled_vertices)} vértices escalados encontrados.")

    # --- Passo 6: Gerar G-code ---
    final_gcode = generate_gcode_from_vertices(scaled_vertices, base_params)
    
    return final_gcode

# ==============================================================================
# 3. FUNÇÕES DE EXEMPLO DE USO
# ==============================================================================

def create_mock_images():
    """
    Cria duas imagens de mock (desenho técnico simples)
    para o script poder ser executado.
    """
    print("[LOG] Criando imagens mock para o teste...")
    
    # --- Vista de Topo (Retângulo de 400x200) ---
    top_img = np.ones((300, 500), dtype=np.uint8) * 255 # Fundo branco
    
    # Desenha o contorno da peça (preto)
    cv2.rectangle(top_img, (50, 100), (450, 200), (0, 0, 0), 2) # Retângulo (400px larg)
    
    # Adiciona a cota "400"
    cv2.putText(top_img, "400", (225, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.line(top_img, (50, 70), (50, 90), (0,0,0), 1)
    cv2.line(top_img, (450, 70), (450, 90), (0,0,0), 1)
    cv2.line(top_img, (50, 80), (450, 80), (0,0,0), 1)
    
    cv2.imwrite("top_view_mock.png", top_img)
    
    # --- Vista de Perfil (Profundidade de 50) ---
    profile_img = np.ones((150, 200), dtype=np.uint8) * 255 # Fundo branco
    
    # Desenha a peça
    cv2.rectangle(profile_img, (25, 75), (125, 125), (0, 0, 0), 2) # Retângulo (50px alt)
    
    # Adiciona a cota "50"
    cv2.putText(profile_img, "50", (140, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.line(profile_img, (130, 75), (150, 75), (0,0,0), 1)
    cv2.line(profile_img, (130, 125), (150, 125), (0,0,0), 1)
    cv2.line(profile_img, (140, 75), (140, 125), (0,0,0), 1)
    
    cv2.imwrite("profile_view_mock.png", profile_img)
    
    print("[LOG] Imagens 'top_view_mock.png' e 'profile_view_mock.png' criadas.")

# ==============================================================================
# 4. EXEMPLO DE USO (Simulando o Backend)
# ==============================================================================

if __name__ == "__main__":
    
    # --- 0. Configuração (AJUSTE OBRIGATÓRIO) ---
    # Descomente e ajuste a linha abaixo para o caminho da sua instalação do Tesseract
    try:
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        pytesseract.get_tesseract_version() # Testa se o caminho é válido
        print("[LOG] Tesseract OCR encontrado.")
    except Exception as e:
        print("="*50)
        print("!! ERRO: Tesseract OCR não encontrado !!")
        print(f"Verifique o caminho em 'pytesseract.pytesseract.tesseract_cmd'")
        print("Faça o download em: https://github.com/UB-Mannheim/tesseract/wiki")
        print("="*50)
        exit() # Encerra se o Tesseract não for encontrado
    
    # --- 1. Gerar Imagens de Teste ---
    create_mock_images()
    
    # --- 2. Simular Upload (Lendo bytes dos arquivos) ---
    try:
        with open("top_view_mock.png", "rb") as f:
            top_bytes = f.read()
        
        with open("profile_view_mock.png", "rb") as f:
            profile_bytes = f.read()
    except FileNotFoundError:
        print("[ERRO] Não foi possível ler os arquivos mock.")
        exit()
        
    # --- 3. Definir Parâmetros Iniciais (Vindos do Frontend) ---
    params = {
        "fileName": "TCC_Exemplo_Retangulo",
        "units": "G21", # mm
        "spindleSpeed": 1200,
        "safetyZ": 10.0,
        "feedRate": 150.0
        # 'cutDepth' será adicionado automaticamente
    }
    
    # --- 4. Executar o Processo Completo ---
    try:
        gcode = process_and_generate_gcode(
            top_view_bytes=top_bytes,
            profile_view_bytes=profile_bytes,
            base_params=params
        )
        
        print("\n" + "="*50)
        print("--- G-CODE GERADO COM SUCESSO ---")
        print(gcode)
        print("="*50)
        
        # --- 5. Salvar o resultado ---
        output_filename = "resultado.gcode"
        with open(output_filename, "w") as f:
            f.write(gcode)
        print(f"\n[LOG] G-code salvo em '{output_filename}'")
        
    except Exception as e:
        print(f"\n--- ERRO NO PROCESSAMENTO ---")
        print(e)