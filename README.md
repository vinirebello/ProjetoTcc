# 🏭 G-Code Generator: Visão Computacional para CNC

> **Projeto de Trabalho de Conclusão de Curso**
> **Curso:** Engenharia de Software

Este projeto consiste em uma aplicação web Fullstack desenvolvida para automatizar a criação de rotas de usinagem (G-Code) para fresadoras verticais CNC. O sistema processa imagens de desenhos 2D simples, detecta a geometria da peça e suas dimensões reais, e gera o código de máquina pronto para execução.


## 📖 Sobre o Projeto

A programação manual de máquinas CNC  pode ser trabalhosa e propensa a erros humanos. Este software visa simplificar esse processo para geometrias 2D, permitindo que o operador faça o upload de um desenho (foto ou scan), configure os parâmetros de corte e receba o arquivo `.gcode` instantaneamente. O projeto visa simplificar o entendimento inicial quando se esta começando a aprender códigos CNC, mantendo um interface mais amigável e prática, sem necessidade de desenhos altamente técnicos, sendo um uso simples e prático.

O diferencial técnico é o uso de **Visão Computacional** para extrair o contorno da peça e **OCR (Reconhecimento Óptico de Caracteres)** para ler as cotas da imagem e calcular a escala automaticamente, sem necessidade de informar as dimensões manualmente.

---

## 🚀 Funcionalidades

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

---

## 🛠️ Arquitetura e Tecnologias

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

## ⚙️ Pré-requisitos

Para executar o projeto, você precisará das seguintes ferramentas instaladas:

1.  **Node.js** e **npm** (Gerenciador de pacotes do Node).
2.  **Python 3.8+** (Certifique-se de adicionar ao PATH).
3.  **MongoDB Community Server** (Rodando localmente ou via Docker).
4.  **Tesseract OCR (Essencial):**
    * O Python precisa do executável do Tesseract instalado no sistema operacional.
    * [Download para Windows](https://github.com/UB-Mannheim/tesseract/wiki).
    * *Nota:* Verifique se o caminho no arquivo `api.py` (`tesseract_cmd`) corresponde ao local de instalação.

---

## ⚡ Instalação e Execução

Siga os passos abaixo em dois terminais diferentes (um para o backend, outro para o frontend).

### 1. Configurando o Backend (Python)

```bash
# Entre na pasta da API
cd backend

# (Opcional) Crie um ambiente virtual
python -m venv venv

# Ative o ambiente virtual
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate

# Instale as dependências
pip install fastapi uvicorn opencv-python pytesseract numpy pymongo python-multipart

# Inicie o servidor
uvicorn api:app --reload
