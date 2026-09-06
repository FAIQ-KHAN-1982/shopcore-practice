from sqlalchemy.orm import Session
from App.Schemas import CategoryCreate
from App.Models import Categories

def AddCategory(data: CategoryCreate, db: Session):
    new_category = Categories(
        name=data.name,
        slug=data.slug,
        description=data.description,
        image_url=data.image_url,
        parent_id=data.parent_id,
        sort_order=data.sort_order,
        is_active=True
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category