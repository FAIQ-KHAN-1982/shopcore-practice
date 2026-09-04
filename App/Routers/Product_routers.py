from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from App.Database_Setup import get_db
from App.Product_Models import Categories
from App.Security import get_current_user, RoleChecker
from App.Models import User

router = APIRouter()

@router.put("/admin/categories", dependencies=[Depends(RoleChecker(["admin", "superadmin"]))], tags=["Products"])
def add_category(data: UpdateUserByAdmin, db: Session = Depends(get_db)):
    return AdminUpdateUser(data, db)