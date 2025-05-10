from pymongo import MongoClient
import os

client = MongoClient(os.getenv("MONGODB_URI"))
db = client["schedule_db"]
collection = db["schedules"]

def save_schedule(user_id, dates):
    document = {
        "user_id": user_id,
        "dates": dates
    }
    collection.insert_one(document)

def get_all_schedules():
    return list(collection.find())
