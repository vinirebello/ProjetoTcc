import sqlite3

DATABASE_FILE = 'database/project.db'

def connect_db():
    """Cria e retorna uma conexão com o banco de dados."""
    return sqlite3.connect(DATABASE_FILE)

def setup_database():
    """Cria a tabela 'drawings' se ela não existir."""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS drawings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL,
            gcode_path TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def insert_drawing_record(file_name, file_path, status="pending"):
    """Insere um novo registro de desenho no banco de dados."""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO drawings (file_name, file_path, status)
        VALUES (?, ?, ?)
    ''', (file_name, file_path, status))
    
    conn.commit()
    conn.close()
    
    print(f"Registro de '{file_name}' inserido com sucesso!")

def update_drawing_status(file_name, new_status, gcode_path=None):
    """Atualiza o status e, opcionalmente, o caminho do G-code."""
    conn = connect_db()
    cursor = conn.cursor()

    if gcode_path:
        cursor.execute('''
            UPDATE drawings
            SET status = ?, gcode_path = ?
            WHERE file_name = ?
        ''', (new_status, gcode_path, file_name))
    else:
        cursor.execute('''
            UPDATE drawings
            SET status = ?
            WHERE file_name = ?
        ''', (new_status, file_name))
    
    conn.commit()
    conn.close()
    
    print(f"Status de '{file_name}' atualizado para '{new_status}'.")

# Para testar a criação da tabela
if __name__ == "__main__":
    setup_database()
    print("Banco de dados configurado com sucesso!")