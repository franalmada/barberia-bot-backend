from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, DECIMAL, Text
from sqlalchemy.orm import relationship
from database import Base
import datetime

# 1. Modelo de Negocio
class Negocio(Base):
    __tablename__ = "negocios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    telefono_contacto = Column(String(20))
    timezone = Column(String(50), default='America/Asuncion') # Agregado
    plan_suscripcion = Column(String(20), default='basico')    # Agregado
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow) # Agregado

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id", ondelete="CASCADE"))
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(20))  # owner, admin, staff
    nombre = Column(String(100))

# 2. Modelo de Servicio
class Servicio(Base):
    __tablename__ = "servicios"
    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id", ondelete="CASCADE"))
    nombre = Column(String(100), nullable=False)
    duracion_minutos = Column(Integer, nullable=False)
    precio = Column(DECIMAL(10, 2), nullable=False)
    activo = Column(Boolean, default=True)

# 3. Modelo de Staff (Barberos)
class Staff(Base):
    __tablename__ = "staff"
    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id", ondelete="CASCADE"))
    nombre = Column(String(100), nullable=False)
    telefono = Column(String(20))
    activo = Column(Boolean, default=True)

# 4. Modelo de Cliente
class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id", ondelete="CASCADE"))
    nombre = Column(String(100))
    telefono_whatsapp = Column(String(20), nullable=False)
    fecha_registro = Column(DateTime, default=datetime.datetime.utcnow)

# 5. Modelo de Turno
class Turno(Base):
    __tablename__ = "turnos"
    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id", ondelete="CASCADE"))
    staff_id = Column(Integer, ForeignKey("staff.id"))
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    servicio_id = Column(Integer, ForeignKey("servicios.id"))
    
    fecha_hora_inicio = Column(DateTime, nullable=False)
    fecha_hora_fin = Column(DateTime, nullable=False)
    estado = Column(String(20)) # pendiente, confirmado, cancelado, realizado, bloqueado
    origen = Column(String(20)) # bot_whatsapp, manual_admin
    notas = Column(Text)        # Agregado
    created_at = Column(DateTime, default=datetime.datetime.utcnow) # Agregado
    
    cliente = relationship("Cliente")
    servicio = relationship("Servicio")
    staff = relationship("Staff")

# 6. Modelo de Logs de WhatsApp (Nuevo)
class WhatsAppLog(Base):
    __tablename__ = "whatsapp_logs"
    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"))
    cliente_telefono = Column(String(20))
    mensaje_enviado = Column(Text)
    mensaje_recibido = Column(Text)
    error_log = Column(Text)
    fecha = Column(DateTime, default=datetime.datetime.utcnow)