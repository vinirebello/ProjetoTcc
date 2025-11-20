import cv2
import numpy as np

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
    
create_mock_images()