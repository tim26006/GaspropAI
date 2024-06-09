from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import logging
from additional_questions import *
from AI import AI_ASSISTANT
from pydantic import BaseModel, EmailStr, Field
from  find_places import  find_places_features
import json


logging.basicConfig(level=logging.INFO)
app = FastAPI()
assistant = AI_ASSISTANT()


origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://localhost:5175",
    "http://localhost:5174",

]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)



class Message(BaseModel):
    text: str


@app.post("/api/messages")
def read_root(message:Message):
    response = assistant.get_answer(str(message.text))
    print(response)
    features = find_places_features(response)
    print (features)
    return {"response":features}


class UserRegistration(BaseModel):
    fio: str
    email: str
    organization: str
    inn: str
    website: str
    industry: str
    country: str
    city: str
    position: str
    password: str

@app.post("/api/register")
async def register_user(user: UserRegistration):
    return {"message": "Пользователь успешно зарегистрирован"}


#uvicorn main:app - для запуска