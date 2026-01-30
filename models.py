from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, DECIMAL, Text
from sqlalchemy.orm import relationship
from database import Base
import datetime

# 1. Modelo de Negocio
class Negocio(Base):
    __tablename__ = "negocios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    telefono_contacto = Column(String)
    activo = Column(Boolean, default=True)


class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"))
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    rol = Column(String)  # owner, admin, staff
    nombre = Column(String)

# 2. Modelo de Servicio
class Servicio(Base):
    __tablename__ = "servicios"
    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"))
    nombre = Column(String)
    duracion_minutos = Column(Integer)
    precio = Column(DECIMAL(10, 2))
    activo = Column(Boolean, default=True)

# 3. Modelo de Staff (Barberos)
class Staff(Base):
    __tablename__ = "staff"
    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"))
    nombre = Column(String)
    telefono = Column(String)
    activo = Column(Boolean, default=True)

# 4. Modelo de Cliente
class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"))
    nombre = Column(String)
    telefono_whatsapp = Column(String)

# 5. Modelo de Turno (La clave)
class Turno(Base):
    __tablename__ = "turnos"
    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"))
    staff_id = Column(Integer, ForeignKey("staff.id"))
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    servicio_id = Column(Integer, ForeignKey("servicios.id"))
    
    fecha_hora_inicio = Column(DateTime)
    fecha_hora_fin = Column(DateTime)
    estado = Column(String) # pendiente, confirmado, cancelado
    origen = Column(String) # bot_whatsapp, manual_admin
    
    # Relaciones (Para poder acceder a los datos fácilmente)
    cliente = relationship("Cliente")
    servicio = relationship("Servicio")
    staff = relationship("Staff")

