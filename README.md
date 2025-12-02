# Gerador automático de G-code

> **Projeto de Trabalho de Conclusão de Curso**

> **Curso:** Engenharia de Software

Este projeto consiste em uma aplicação web Fullstack desenvolvida para automatizar a criação de rotas de usinagem (G-Code) para fresadoras verticais CNC. O sistema processa imagens de desenhos 2D simples, detecta a geometria da peça e suas dimensões reais, e gera o código de máquina pronto para execução.


## Sobre o Projeto

A programação manual de máquinas CNC  pode ser trabalhosa e propensa a erros humanos. Este software visa simplificar esse processo para geometrias 2D, permitindo que o operador faça o upload de um desenho (foto ou arquivos de imagem), configure os parâmetros de corte e receba o arquivo `.gcode` instantaneamente. O projeto visa simplificar o entendimento inicial quando se esta começando a aprender códigos CNC, mantendo uma interface mais amigável, sem necessidade de desenhos altamente técnicos, sendo um uso simples e prático.

O diferencial técnico é o uso de **Visão Computacional** para extrair o contorno da peça e **OCR (Reconhecimento Óptico de Caracteres)** para ler as cotas da imagem e calcular a escala automaticamente, sem necessidade de informar as dimensões manualmente.

A aplicação pode ser visualizada acessando: https://projeto-tcc-phi.vercel.app 

## Funcionalidades

* **Processamento de Imagem:** Upload de arquivos `.png`, `.jpg` ou `.jpeg`.
* **Detecção Automática de Geometria:** Identificação de perfis fechados e contornos da peça.
* **Escalonamento Inteligente:** Leitura automática de números na imagem para converter pixels em milímetros.
* **Parametrização de Usinagem:** Interface para ajuste de:
    * Rotação do Spindle (RPM).
    * Taxa de Avanço (Feed Rate).
    * Profundidade de Corte (Z-Depth).
    * Altura de Segurança (Safe Z).
    * Unidades (mm/pol).
* **Visualização e Exportação:** Preview do código G em tela e download direto do arquivo.

## Requisitos Funcionais (RF):
* RF001: O sistema deve permitir ao usuário carregar uma imagem 2D da peça (formatos comuns como PNG, JPEG).
* RF002: O sistema deve permitir ao usuário definir um fator de escala na imagem (ex: por pixels/mm ou informando uma medida de referência).
* RF003: O sistema deve detectar automaticamente bordas e contornos da peça na imagem.
* RF004: O sistema deve identificar geometrias básicas como linhas, círculos e arcos a partir dos contornos detectados.
* RF005: O sistema deve extrair as dimensões precisas (comprimento, largura, raio, diâmetro) das geometrias identificadas.
* RF006: O sistema deve gerar o código G (g-code) para as operações de usinagem baseadas nas dimensões extraídas.
* RF007: O sistema deve permitir ao usuário especificar parâmetros de usinagem (ex: profundidade de corte, velocidade de avanço, velocidade do spindle).
* RF008: O sistema deve permitir ao usuário visualizar o g-code gerado antes da exportação.
* RF009: O sistema deve permitir a exportação do g-code gerado para um arquivo de texto (.nc).
* RF010: O sistema deve exibir mensagens de erro claras em caso de falha no processamento da imagem ou geração do g-code.

## Requisitos Não-Funcionais (RNF):
* RNF001: O processamento da imagem e a geração do g-code devem ser concluídos em no máximo 5 segundos para imagens de tamanho médio (ex: 1920x1080 pixels).
* RNF002): A interface do usuário deve ser intuitiva e fácil de usar, mesmo para usuários com pouca experiência em visão computacional ou programação CNC.
* RNF003: O g-code gerado deve ser sintaticamente correto e compatível com as máquinas CNC padrão.
* RNF004): O software deve ser executável em sistemas operacionais Windows e Linux.
* RNF005): O código-fonte deve ser bem documentado e modular, facilitando futuras extensões e correções.
* RNF006): O sistema não deve exigir privilégios elevados para sua execução e não deve manipular dados sensíveis

---

## Arquitetura e Tecnologias

O sistema foi desenvolvido utilizando uma arquitetura de microsserviços simples, separando o cliente (Frontend) do servidor de processamento (Backend).

### **Frontend (Interface)**
* **React.js:** Biblioteca principal para construção da UI.
* **Axios:** Cliente HTTP para comunicação com a API.
* **CSS3:** Estilização responsiva.

### **Backend (API & Processamento)**
* **Python 3.x:** Linguagem base.
* **FastAPI:** Framework moderno e de alta performance para a API REST.
* **OpenCV (cv2):** Biblioteca de visão computacional para pré-processamento e detecção de contornos.
* **Pytesseract:** Wrapper para o motor **Tesseract OCR** (Google) para leitura de texto em imagens.
* **NumPy:** Cálculos matemáticos vetoriais.

### **Banco de Dados**
* **MongoDB:** Banco NoSQL para armazenamento do histórico de arquivos e parâmetros.

---

## Pré-requisitos

Para executar o projeto, você precisará das seguintes ferramentas instaladas:

1.  **Node.js** e **npm** (Gerenciador de pacotes do Node).
2.  **Python 3.9+**
3.  **MongoDB Community Server** (Rodando localmente ou via Docker).
4.  **Tesseract OCR (Essencial):**
    * O Python precisa do executável do Tesseract instalado no sistema operacional.
    * [Download para Windows](https://github.com/UB-Mannheim/tesseract/wiki).
    * *Nota:* Verifique se o caminho no arquivo `api.py` (`tesseract_cmd`) corresponde ao local de instalação.

---

## Instalação e Execução

Siga os passos abaixo em dois terminais diferentes (um para o backend, outro para o frontend).

### 1. Configurando o Backend (Python)

```bash
# Entre na pasta da API
cd backend

# (Opcional) Crie um ambiente virtual
python -m venv venv

# Instale as dependências
pip install fastapi uvicorn opencv-python pytesseract numpy pymongo python-multipart

# Inicie o servidor
uvicorn api:app --reload

# Para a aplicação React, va para a pasta do frontend
cd frontend/gcode_generator

#Inicie o app React
npm start


