from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from App.Database_Setup import get_db
from App.Models import User, Address
from App.Schemas import (
    UserResponse,
    UpdateProfileRequest,
    FieldsForAddress,
    defaultaddress,
)
from App.Security import get_current_user, RoleChecker
from App.Services.User_service import (
    add_address,
    show_my_address,
    delete_address_by_id,
    update_address_by_id,
    default_address,
)

router = APIRouter()

# ==================== USER MANAGEMENT ROUTES ====================

@router.get("/users/me", tags=["User"])
def my_profile(current_user: User = Depends(get_current_user)):
    return {
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "phone": current_user.phone,
        "role": current_user.role
    }

@router.put("/users/me", response_model=UserResponse, tags=["User"])
def update_profile(data: UpdateProfileRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.first_name:
        current_user.first_name = data.first_name
    if data.last_name:
        current_user.last_name = data.last_name
    if data.phone:
        current_user.phone = data.phone
    db.commit()
    db.refresh(current_user)
    return current_user

@router.delete("/users/me", tags=["User"])
def delete_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(current_user)
    db.commit()
    return {"message": "Account deleted successfully"}

@router.post("/users/me/addresses", dependencies=[Depends(RoleChecker(["buyer"]))], tags=["User"])
def address_adding(data: FieldsForAddress, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    addresses = db.query(Address).filter(Address.user_id == current_user.id).all()
    if len(addresses) >= 10:
        raise HTTPException(
            status_code=400,
            detail="You can only have a maximum of 10 addresses."
        ) 
    add_address(data, current_user.id, db)
    return {"message": "Address added successfully"}

@router.get("/users/me/addresses", tags=["User"])
def show_address(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return show_my_address(current_user, db)

@router.delete("/users/me/addresses/{address_id}", tags=["User"])
def delete_address(address_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    delete_address_by_id(address_id, current_user, db)
    return {"message": "Address deleted successfully"}

@router.put("/users/me/addresses/{address_id}", tags=["User"])
def update_address(data: FieldsForAddress, address_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return update_address_by_id(data, address_id, current_user, db)

@router.put("/users/me/addresses/{address_id}/default", tags=["User"])
def default_the_address(data: defaultaddress, address_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return default_address(data, address_id, current_user, db)

