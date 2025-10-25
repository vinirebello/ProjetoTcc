import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from datetime import datetime

MONGO_URI = "mongodb+srv://vrebello21_db_user:kzQgcaZNiAlcwfNv@cluster.t7vznud.mongodb.net/"
DATABASE_NAME = "ProjetcDatabase"
COLLECTION_NAME = "data"

def connect_db():
    
    try:
        con = MongoClient(MONGO_URI)
        con.admin.command('ping') 
        print("Conectado ao MongoDB com sucesso!")
        db = con.get_database(DATABASE_NAME)
        return db
    except ConnectionFailure as e:
        print(f"Erro ao conectar ao MongoDB: {e}")
        return None

def insert_drawing_record():
    
    db = connect_db()

    if db is not None:
        collection = db.get_collection(COLLECTION_NAME)
        drawing_record = {
            # "file_name": file_name,
            # "file_path": file_path,
            "upload_date": datetime.now(),
            "status": "pending",
            # "gcode_path": None
        }
        result = collection.insert_one(drawing_record)
        print(f"Registro de dado inserido com o ID: {result.inserted_id}")
        return result.inserted_id
    else:
        print("Erro ao inserir dados no banco")
    
def update_drawing_status(file_id, new_status, gcode_path=None):
    """Atualiza o status e, opcionalmente, o caminho do G-code de um registro."""
    db = connect_db()
    if db is not None:
        collection = db.get_collection(COLLECTION_NAME)
        update_data = {"status": new_status}
        if gcode_path:
            update_data["gcode_path"] = gcode_path
            
        from bson.objectid import ObjectId
        
        result = collection.update_one(
            {"_id": ObjectId(file_id)},
            {"$set": update_data}
        )
        if result.modified_count > 0:
            print(f"Status do registro {file_id} atualizado para '{new_status}'.")
        else:
            print(f"Nenhum registro encontrado com o ID {file_id}.")

def get_all_drawings():
    """Retorna todos os registros de desenhos da coleção."""
    db = connect_db()
    if db:
        collection = db[COLLECTION_NAME]
        return list(collection.find({}))
    return []
