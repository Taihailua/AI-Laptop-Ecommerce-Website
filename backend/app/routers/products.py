from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os
import shutil
import json
from uuid import uuid4
from .. import schemas, crud, models
from ..database import get_db

router = APIRouter(
    prefix="/api/products",
    tags=["Products"]
)

UPLOAD_DIR = "uploads"

# Override existing Create/Update to handle File
@router.post("/", response_model=schemas.ProductResponse)
def create_product(
    name: str = Form(...),
    brand: str = Form(...),
    price: float = Form(...),
    stock_quantity: int = Form(...),
    image_url: Optional[str] = Form(None),
    specs: Optional[str] = Form(None), # JSON string
    image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    final_image_url = image_url
    
    # Handle File Upload
    if image_file:
        filename = f"{uuid4()}_{image_file.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        final_image_url = f"http://localhost:8000/static/{filename}" # Simple local URL

    # Parse Specs
    specs_dict = None
    if specs:
        try:
            specs_dict = json.loads(specs)
        except:
            pass
            
    # Create DB Object
    db_product = models.Product(
        name=name,
        brand=brand,
        price=price,
        stock_quantity=stock_quantity,
        image_url=final_image_url,
        specs=specs_dict
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.put("/{product_id}", response_model=schemas.ProductResponse)
def update_product(
    product_id: int,
    name: str = Form(...),
    brand: str = Form(...),
    price: float = Form(...),
    stock_quantity: int = Form(...),
    image_url: Optional[str] = Form(None),
    specs: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Update logic
    product.name = name
    product.brand = brand
    product.price = price
    product.stock_quantity = stock_quantity
    
    # Update image only if new file or new URL provided (otherwise keep old)
    if image_file:
        filename = f"{uuid4()}_{image_file.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        product.image_url = f"http://localhost:8000/static/{filename}"
    elif image_url is not None:
         # Only update if image_url is explicitly sent (not None/empty if using Form default)
         # If form sends empty string, it might mean remove image? 
         # Let's assume sending text updates it.
         if len(image_url) > 0:
            product.image_url = image_url
    
    if specs:
        try:
            product.specs = json.loads(specs)
        except:
            pass

    db.commit()
    db.refresh(product)
    return product

@router.get("/", response_model=list[schemas.ProductResponse])
def read_products(skip: int = 0, limit: int = 100, search: str = None, db: Session = Depends(get_db)):
    return crud.get_products(db, skip=skip, limit=limit, search=search)

@router.get("/{product_id}", response_model=schemas.ProductResponse)
def read_product(product_id: int, db: Session = Depends(get_db)):
    db_product = crud.get_product(db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


# REPLACES: The old Pydantic-based create/update methods below are removed to avoid conflict.
# The new Form-based methods above handle both text and file uploads.


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": f"Deleted product #{product_id}"}
