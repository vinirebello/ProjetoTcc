import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
from database import insert_drawing_record, update_drawing_status

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
    
    try:
        # Pega o nome do arquivo a partir do caminho
        nome_arquivo = filePath.split('/')[-1]

        # 1. Salva o registro no banco de dados com status "pending"
        print("Salvando registro no banco")
        insert_drawing_record()

    
        # print(f"Analisando o arquivo: {filePath}")
        # dados_da_peca = dimension_extractor.extrair_cotas(filePath)

        # 3. Gera o G-code (simulado)
        # gcode = "G-code gerado para a peça..." 

        # Salva o arquivo G-code e obtém seu caminho
        # gcode_file_path = f"data/gcode_outputs/{nome_arquivo.replace('.png', '.gcode')}"
        # with open(gcode_file_path, "w") as f:
        #     f.write(gcode)

        # 4. Atualiza o status no banco de dados para "processed"
        # update_drawing_status(nome_arquivo, "processed", gcode_file_path)

        # 5. Exibe o G-code na tela
        textArea.delete(1.0, tk.END)
        textArea.insert(tk.END, "aaaaaaa")

        messagebox.showinfo("Sucesso", "G-Code gerado e salvo com sucesso!")

    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro: {e}")
    
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