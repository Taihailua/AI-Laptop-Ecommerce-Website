from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
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
PAUSE_FLAG_KEY = "__business_paused__"
PAUSE_AT_KEY = "__business_paused_at__"


def _normalize_specs(specs: object) -> dict:
    return dict(specs) if isinstance(specs, dict) else {}


def _is_product_paused(product: models.Product) -> bool:
    specs = _normalize_specs(product.specs)
    paused_flag = specs.get(PAUSE_FLAG_KEY, False)
    if isinstance(paused_flag, str):
        return paused_flag.strip().lower() in {"1", "true", "yes", "on"}
    return bool(paused_flag)


def _merge_internal_spec_flags(existing_specs: object, incoming_specs: object) -> dict:
    merged = _normalize_specs(incoming_specs)
    existing = _normalize_specs(existing_specs)
    for key in (PAUSE_FLAG_KEY, PAUSE_AT_KEY):
        if key in existing and key not in merged:
            merged[key] = existing[key]
    return merged

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
            parsed_specs = json.loads(specs)
            product.specs = _merge_internal_spec_flags(product.specs, parsed_specs)
        except:
            pass

    db.commit()
    db.refresh(product)
    return product

@router.get("/", response_model=list[schemas.ProductResponse])
def read_products(
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    include_paused: bool = False,
    db: Session = Depends(get_db),
):
    return crud.get_products(db, skip=skip, limit=limit, search=search, include_paused=include_paused)

@router.get("/{product_id}", response_model=schemas.ProductResponse)
def read_product(product_id: int, include_paused: bool = False, db: Session = Depends(get_db)):
    db_product = crud.get_product(db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if not include_paused and _is_product_paused(db_product):
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@router.patch("/{product_id}/business-status", response_model=schemas.ProductResponse)
def update_product_business_status(product_id: int, is_paused: bool, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    specs = _normalize_specs(product.specs)
    specs[PAUSE_FLAG_KEY] = bool(is_paused)
    if is_paused:
        specs[PAUSE_AT_KEY] = str(uuid4())
    else:
        specs.pop(PAUSE_AT_KEY, None)
    product.specs = specs

    db.commit()
    db.refresh(product)
    return product


# REPLACES: The old Pydantic-based create/update methods below are removed to avoid conflict.
# The new Form-based methods above handle both text and file uploads.


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Do not allow deleting products that already appear in order history.
    has_order_items = db.query(models.OrderItem.id).filter(models.OrderItem.product_id == product_id).first()
    if has_order_items:
        raise HTTPException(
            status_code=409,
            detail="Không thể xóa sản phẩm vì đã phát sinh trong đơn hàng. Bạn có thể tạm ngừng kinh doanh thay vì xóa.",
        )

    db.delete(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Không thể xóa sản phẩm vì đang có dữ liệu liên quan.",
        )

    return {"message": f"Deleted product #{product_id}"}
