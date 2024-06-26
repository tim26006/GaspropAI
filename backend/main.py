from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import logging
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from additional_questions import *
from AI import *
from pydantic import BaseModel, EmailStr, Field
from  find_places import  find_places_features
from questions import  get_questions, define_them_question
from  prepare_query import prepare_data
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from jose import jwt
from jose.exceptions import JWTError
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException
from auth import *
from fastapi.security import OAuth2PasswordBearer
from prepare_compare import prepare_data_to_compare
from db import *
from models import *
from compare import  compare
from  report_test import *
from hepls  import  *
from typing import List
import json



#uvicorn main:app

logging.basicConfig(level=logging.INFO)
app = FastAPI()




global start_message
global number_of_question
global query_to_bot

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

start_message = True
number_of_question = 0
query_to_bot = " "
user_answers = []

@app.post("/api/messages")
def read_root(message:Message):
    if not(define_them_question(message)):
        global start_message, questions_to_user, query
        global number_of_question
        global query_to_bot
        global user_answers
        if start_message:  # Здесь обрабатывается начальный запрос и формируются дополнительные вопросы
            query_to_bot = str(message)
            questions_to_user = get_questions(str(message))
            start_message = False
        if number_of_question< len(questions_to_user): # Задаем вопросы пока не кончатся
            question = questions_to_user[number_of_question]
            user_answers.append(message)
            number_of_question += 1
            if number_of_question == len(questions_to_user):
                return {"response": question,"last":"True", "features": "нема"}
            else:
                return {"response": question, "last": "False", "features": "нема"}
        elif number_of_question == len(questions_to_user):
            # Код, где подбирается площадка
            query = prepare_data (query_to_bot, questions_to_user, user_answers ) ## Сформировали запрос для нейронки
            names = place_names(query)  ## Отправили запрос нейронке и получили найденные обьекты
            start_message = True
            number_of_question = 0
            questions_to_user = []
            user_answers = []
            query_to_bot = []
            features = find_places_features(names)
            aye = features[0]
            suka = features[1]
            blyat = features[2]
            return {"response": "Нашел несколько площадок для Вас", "features":aye, "answer2":suka, "answer3":blyat, "otvet":True}
    else:
        lgots = help(str(message))
        return {"response": lgots[0], 'lgots':1}

# Routes
@app.post("/api/register", response_model=dict)
async def register_user(user: UserRegistration, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    new_user = User(
        fio=user.fio,
        email=user.email,
        organization=user.organization,
        inn=user.inn,
        website=user.website,
        industry=user.industry,
        country=user.country,
        city=user.city,
        position=user.position,
        hashed_password=hashed_password
    )
    db.add(new_user)
    try:
        db.commit()
        db.add(new_user)
        db.refresh(new_user)
        logger.info("User registered successfully: %s", user.email)
    except Exception as e:
        db.rollback()
        logger.error("Error committing the new user to the database: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"message": f"Пользователь {user.fio} успешно зарегистрирован"}


@app.post("/api/login", response_model=Token)
async def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = authenticate_user(db, user.email, user.password)
    if not db_user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
    data={"sub": db_user.email}, expires_delta=access_token_expires)

    return {"access_token": access_token, "token_type": "bearer"}



class UserInfo(BaseModel):
    fio: str
    email: str
    organization: str
    inn: str
    website: str
    industry: str
    country: str
    city: str
    position: str

    class Config:
        orm_mode = True

class ReportResponseSchema(BaseModel):
    id: int
    email: str
    date: str
    link: str

    class Config:
        orm_mode = True
        from_attributes = True


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.get("/api/user_info", response_model=UserInfo)
async def get_user_info(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user



@app.post("/api/compare")
async def compare_objects(request: Request):
    body = await request.json()
    prepare_data = prepare_data_to_compare(body)
    compared = compare(str(prepare_data))
    print(compared)
    return {"message": compared}



@app.post("/api/report")
async def make_report(request: Request):
    body = await request.json() #массив json
    return {"report_link": report_data(body)}



@app.post("/api/save_report")
async def save_report(request: SaveReportRequest, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception

    # Save the report data to the database
    new_report = Report(
        email=user.email,
        date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        link=request.report_link
    )
    db.add(new_report)
    try:
        db.commit()
        db.refresh(new_report)
        logger.info("Report saved successfully for user: %s", user.email)
    except Exception as e:
        db.rollback()
        logger.error("Error committing the new report to the database: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"message": "Report saved successfully"}


@app.get("/api/get_reports", response_model=List[ReportResponseSchema])
async def get_reports(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception

    reports = db.query(Report).filter(Report.email == email).all()
    report_dicts = [ReportResponseSchema.from_orm(report).dict() for report in reports]
    return report_dicts

