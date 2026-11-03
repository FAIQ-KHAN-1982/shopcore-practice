from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from App.Database_Setup import get_db
from App.Schemas import UserResponse, UpdateUserByAdmin
from App.Security import RoleChecker
from App.Services.admin_service import (
    ListUsers,
    GetUserByID,
    DeleteUser,
    AdminUpdateUser,
)

router = APIRouter()

# ==================== ADMIN ROUTES ====================

@router.get("/admin/users", dependencies=[Depends(RoleChecker(["admin", "superadmin"]))], tags=["Admin"])
def get_users(db: Session = Depends(get_db)):
    return ListUsers(db)

@router.get("/admin/users/{id}", dependencies=[Depends(RoleChecker(["admin", "superadmin"]))], tags=["Admin"])
def get_user_ID(id: int, db: Session = Depends(get_db)):
    return GetUserByID(db, id)

@router.delete("/admin/users/{id}", dependencies=[Depends(RoleChecker(["admin", "superadmin"]))], tags=["Admin"])
def delete_user(id: int, db: Session = Depends(get_db)):
    DeleteUser(db, id)
    return {"message": "this user is deleted"}

@router.put("/admin/users/{id}", response_model=UserResponse, dependencies=[Depends(RoleChecker(["admin", "superadmin"]))], tags=["Admin"])
def update_user(data: UpdateUserByAdmin, id: int, db: Session = Depends(get_db)):
    return AdminUpdateUser(data, db, id)

