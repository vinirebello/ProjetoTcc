import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox

window = tk.Tk()
window.title("Gerador de G-Code")
window.geometry("800x800")

def loadFile():
    
    filePath = filedialog.askopenfilename(
        title="Selecione o Desenho",
        filetypes=[("Arquivos de Imagem", "*.png *.jpg *.svg *.dxf")]
    )
    
    if not filePath:
        return
    

frameButtom = tk.Frame(window)
frameButtom.pack(pady=10)

loadButtom = tk.Button(
    frameButtom,
    text="Carregar Desenho",
    command=loadFile,
    font=("Arial", 12)
)

loadButtom.pack(side=tk.LEFT, padx=10)

textArea= scrolledtext.ScrolledText(window, wrap=tk.WORD, width=90, height=30, font=("Courier New", 10))
textArea.pack(pady=10)


window.mainloop()