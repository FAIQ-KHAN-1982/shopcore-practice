from sqlalchemy.orm import Session
from App.Database_Setup import *
from App.Models import *


def get_users(db:Session):
    users = db.query(User).all()
    return users

def get_users_by_ID(db: Session):
    user = db.query(User).all()
    return user