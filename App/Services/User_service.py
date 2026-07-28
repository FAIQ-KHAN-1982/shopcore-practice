from App.Schemas import feilds_for_address
from App.Models import Address
from sqlalchemy.orm import Session


def add_address(data: feilds_for_address, user_id: int, db: Session):

    new_address = Address(
        user_id=user_id,
        full_name=data.full_name,
        phone=data.phone,
        address_line_1=data.address_line_1,
        city=data.city
    )

    db.add(new_address)
    db.commit()
    db.refresh(new_address)

    return new_address
