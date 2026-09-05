from sqlalchemy.orm import Session
from App.Schemas import CategoryCreate

def AddCategory(data: CategoryCreate, db: Session):
    new_category = CategoryCreate(
        name = data.name,
        slug = data.slug,
        description = data.description,
        image_url = data.image_url,
        parent_id = data.parent_id,   
        sort_order = data.sort_order
    )

    
    