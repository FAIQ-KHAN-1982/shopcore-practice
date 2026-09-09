from sqlalchemy.orm import Session
from App.Schemas import CategoryCreateSchema
from App.Models import Categories
from fastapi import HTTPException, status

def AddCategory(data: CategoryCreateSchema, db: Session):
    
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
        parent_id=data.parent_id,
        sort_order=data.sort_order,
        is_active=True
    )
    
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    
    return new_category

def DeleteCategory(id: int, db: Session):
    the_row = db.query(Categories).filter(Categories.id == id).first()
    if not the_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    db.delete(the_row)
    db.commit()
    return "Category deleted successfully"

