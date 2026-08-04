from App.Schemas import feilds_for_address
from App.Models import Address, User
from sqlalchemy.orm import Session
from fastapi import HTTPException, status



def add_address(data: feilds_for_address, data_user_id: int, db: Session):

    new_address = Address(
        user_id=data_user_id,
        full_name=data.full_name,
        phone=data.phone,
        address_line_1=data.address_line_1,
        city=data.city
    )

    db.add(new_address)
    db.commit()
    db.refresh(new_address)

    return new_address

def show_my_address(current_user: User, db: Session):
    data = db.query(Address).filter(Address.user_id == current_user.id).all()
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found"
        )
    return [
        {
            "Name": address.full_name,
            "address": address.address_line_1,
            "phone": address.phone,
            "city": address.city
        }
        for address in data
    ]

def delete_address_by_id(address_id: int, current_user: User, db: Session):
    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_id == current_user.id
    ).first()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found"
        )

    db.delete(address)
    db.commit()
