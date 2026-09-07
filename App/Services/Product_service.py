from sqlalchemy.orm import Session
from App.Schemas import CategoryCreate
from App.Models import Categories
from fastapi import HTTPException, status

def AddCategory(data: CategoryCreate, db: Session):
    
    # Check if category with same slug already exists
    existing_category = db.query(Categories).filter(Categories.slug == data.slug).first()
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Category with this slug already exists"
        )

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