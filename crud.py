from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import timedelta
import models, schemas

# 1. FUNCIÓN AUXILIAR: BUSCAR O CREAR CLIENTE
# Si el cliente ya existe por su teléfono, lo devuelve. Si no, lo crea.
def get_or_create_cliente(db: Session, telefono: str, nombre: str = "Estimado Cliente", negocio_id: int = 1):
    cliente = db.query(models.Cliente).filter(
        models.Cliente.telefono_whatsapp == telefono,
        models.Cliente.negocio_id == negocio_id
    ).first()
    
    if cliente:
        return cliente
    else:
        nuevo_cliente = models.Cliente(
            telefono_whatsapp=telefono,
            nombre=nombre,
            negocio_id=negocio_id
        )
        db.add(nuevo_cliente)
        db.commit()
        db.refresh(nuevo_cliente)
        return nuevo_cliente

# 2. EL ALGORITMO DE DISPONIBILIDAD (Matemática pura)
def check_disponibilidad(db: Session, staff_id: int, inicio, fin):
    # Buscamos turnos que SOLAPEN con el horario deseado.
    # Lógica: Un turno choca si empieza antes de que el nuevo termine Y termina después de que el nuevo empiece.
    choque = db.query(models.Turno).filter(
        models.Turno.staff_id == staff_id,
        models.Turno.estado.in_(['pendiente', 'confirmado']), # Ignoramos los cancelados
        and_(
            models.Turno.fecha_hora_inicio < fin,
            models.Turno.fecha_hora_fin > inicio
        )
    ).first()
    
    # Si choque existe, NO está disponible (False). Si es None, SÍ está disponible (True)
    return choque is None

# 3. FUNCIÓN PRINCIPAL: CREAR TURNO
def create_turno(db: Session, turno: schemas.TurnoCreate):
    # A. Calculamos cuándo termina el turno
    # Primero buscamos cuánto dura el servicio elegido
    servicio = db.query(models.Servicio).filter(models.Servicio.id == turno.servicio_id).first()
    if not servicio:
        raise Exception("Servicio no encontrado")
        
    hora_fin = turno.fecha_hora_inicio + timedelta(minutes=servicio.duracion_minutos)
    
    # B. Validamos Disponibilidad
    if not check_disponibilidad(db, turno.staff_id, turno.fecha_hora_inicio, hora_fin):
        return None # Retornamos vacío para indicar error
        
    # C. Gestionamos al Cliente
    cliente = get_or_create_cliente(db, turno.telefono_cliente, turno.nombre_cliente, turno.negocio_id)
    
    # D. Guardamos el Turno
    db_turno = models.Turno(
        negocio_id=turno.negocio_id,
        staff_id=turno.staff_id,
        cliente_id=cliente.id,
        servicio_id=turno.servicio_id,
        fecha_hora_inicio=turno.fecha_hora_inicio,
        fecha_hora_fin=hora_fin,
        estado="confirmado",
        origen="bot_whatsapp"
    )
    
    db.add(db_turno)
    db.commit()
    db.refresh(db_turno)
    return db_turno