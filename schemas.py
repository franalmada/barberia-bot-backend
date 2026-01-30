from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- ESQUEMAS PARA SERVICIOS ---
class ServicioBase(BaseModel):
    nombre: str
    duracion_minutos: int
    precio: float

class Servicio(ServicioBase):
    id: int
    negocio_id: int
    
    class Config:
        from_attributes = True  # Esto permite leer datos directo de la base de datos

# --- ESQUEMAS PARA STAFF (BARBEROS) ---
class StaffBase(BaseModel):
    nombre: str
    telefono: str

class StaffCreate(StaffBase):
    pass

class Staff(StaffBase):
    id: int
    
    class Config:
        from_attributes = True




# --- ESQUEMAS PARA TURNOS ---

# 1. Lo que recibimos cuando alguien quiere crear un turno
class TurnoCreate(BaseModel):
    negocio_id: int
    staff_id: int
    servicio_id: int
    telefono_cliente: str
    nombre_cliente: Optional[str] = None # Opcional si ya lo conocemos
    fecha_hora_inicio: datetime # Formato: 2026-01-30T10:00:00

# 2. Lo que devolvemos cuando consultan un turno
class Turno(BaseModel):
    id: int
    fecha_hora_inicio: datetime
    fecha_hora_fin: datetime
    estado: str
    
    # Podemos anidar objetos para dar más info
    servicio: Optional[Servicio] = None
    staff: Optional[Staff] = None

    class Config:
        from_attributes = True

        # --- ESQUEMA PARA EL CHAT ---
class MensajeWhatsApp(BaseModel):
    telefono: str
    mensaje: str

    # ---  Este ya lo usamos para recibir datos (Input)
class ServicioCreate(ServicioBase):
    pass

# --- AGREGAR EN SCHEMAS.PY (Para arreglar el error de Cliente) ---

class ClienteBase(BaseModel):
    nombre: str
    telefono_whatsapp: str
    email: str | None = None  # Opcional

class ClienteCreate(ClienteBase):
    pass

class Cliente(ClienteBase):
    id: int
    # fecha_registro: datetime  <-- Opcional si la tienes en models.py

    class Config:
        from_attributes = True