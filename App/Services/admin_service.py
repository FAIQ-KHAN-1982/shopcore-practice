from fastapi import HTTPException
from sqlalchemy.orm import Session
from App.Database_Setup import *
from App.Models import *


def ListUsers(db: Session):
    users = db.query(User).all()
    return users

def GetUserByID(db: Session, id: int):
    users = db.query(User).filter(User.id == id).first()
    return users

def DeleteUser(db: Session, id: int):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(
            status_code = 404,
            detail = "user not found"
        )
    db.delete(user)
    db.commit()
    return {"message":f"user {id} is successfully deleted"}


