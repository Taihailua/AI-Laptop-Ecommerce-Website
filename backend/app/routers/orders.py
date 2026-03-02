from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from .. import schemas, crud, models
from ..database import get_db

router = APIRouter(
    prefix="/api/orders",
    tags=["Orders"]
)

class StatusUpdate(BaseModel):
    status: models.OrderStatus

@router.post("/checkout", response_model=schemas.OrderResponse)
def checkout_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    try:
        db_order = crud.create_order(db=db, order_data=order)
        return db_order
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/track/{phone_number}", response_model=List[schemas.OrderResponse])
def track_order_by_phone(phone_number: str, db: Session = Depends(get_db)):
    orders = crud.get_order_by_phone(db, phone_number=phone_number)
    return orders

@router.get("/", response_model=List[schemas.OrderResponse])
def get_all_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    orders = crud.get_orders(db, skip=skip, limit=limit)
    return orders

@router.patch("/{order_id}/status", response_model=schemas.OrderResponse)
def update_order_status(order_id: int, status_update: StatusUpdate, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = status_update.status
    db.commit()
    db.refresh(order)
    return order
