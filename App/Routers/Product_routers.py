from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from App.Database_Setup import get_db
from App.Models import Categories, User
from App.Security import get_current_user, RoleChecker
from App.Schemas import CategoryCreateSchema
from App.Services.Product_service import AddCategory, DeleteCategory 

router = APIRouter()

# adding delete column feature to category
# adding update to catogory

@router.post("/categories", dependencies=[Depends(RoleChecker(["admin", "superadmin"]))], tags=["Products"])
def add_category(data: CategoryCreateSchema, db: Session = Depends(get_db)):
    new_category = AddCategory(data, db)
    return new_category

@router.delete("/admin/categories/{id}", dependencies=[Depends(RoleChecker(["admin", "superadmin"]))], tags=["Products"])
def delete_category(id: int, db: Session = Depends(get_db)):
    return DeleteCategory(id, db)

@router.put("/admin/categories/{id}", dependencies=[Depends(RoleChecker(["admin", "superadmin"]))], tags=["Products"])
def delete_category(id: int, db: Session = Depends(get_db)):
    return DeleteCategory(id, db)