import pymongo
from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
from datetime import datetime

MONGO_URI = "mongodb+srv://vrebello21_db_user:admin2106@cluster.t7vznud.mongodb.net/"
DATABASE_NAME = "ProjectDatabase"
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

def registerDatabase(initialParams: dict, gcodeResult: str):
    
    db = connect_db()

    if db is not None:
        collection = db.get_collection(COLLECTION_NAME)
        drawing_record = {
            "params": initialParams,
            "gcode": gcodeResult,
            "upload_date": datetime.now(),
        }
        result = collection.insert_one(drawing_record)
        print(f"Registro de dado inserido com o ID: {result.inserted_id}")
        return result.inserted_id
    else:
        print("Erro ao inserir dados no banco")
    
def update_drawing_status(file_id, new_status, gcode_path=None):

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
            
def getFormattedItems(limit=20):

    db = connect_db()
    if db is not None:
        collection = db.get_collection(COLLECTION_NAME)
        
        cursor = collection.find({}).sort("_id", DESCENDING).limit(limit)
        
        history_list = []
        for doc in cursor:

            date_obj = doc.get("upload_date") or doc.get("timestamp")
            
            if isinstance(date_obj, datetime):
                formatted_date = date_obj.strftime("%d/%m/%Y %H:%M")
            else:
                formatted_date = "Data Desconhecida"

            params = doc.get("params", {})

            history_list.append({
                "id": str(doc["_id"]),
                "filename": params.get("fileName") or doc.get("filename", "Sem nome"),
                "timestamp": formatted_date,
                "params": params,
                "gcode": doc.get("gcode", "")
            })
        return history_list
    return []

def deleteItem(file_id: str):
    db = connect_db()
    if db is not None:
        collection = db.get_collection(COLLECTION_NAME)
        result = collection.delete_one({"_id": ObjectId(file_id)})
        return result.deleted_count > 0
    return False

def getAllItems():
    db = connect_db()
    if db:
        collection = db[COLLECTION_NAME]
        return list(collection.find({}))
    return []
