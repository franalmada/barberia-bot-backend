from fastapi import FastAPI, Depends, HTTPException, Form, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from database import get_db
import models, schemas, crud

app = FastAPI(title="Barbería API", version="1.0")

# --- RUTA DE INICIO ---
@app.get("/")
def read_root():
    return {"mensaje": "API de Reservas Funcionando 🚀"}

# --- RUTAS DE CONSULTA (GET) ---

# 1. Listar Servicios
@app.get("/servicios/", response_model=List[schemas.Servicio])
def listar_servicios(db: Session = Depends(get_db)):
    return db.query(models.Servicio).filter(models.Servicio.activo == True).all()

# 2. Listar Barberos
@app.get("/staff/", response_model=List[schemas.Staff])
def listar_staff(db: Session = Depends(get_db)):
    return db.query(models.Staff).filter(models.Staff.activo == True).all()

# --- RUTAS DE ACCIÓN (POST) - ADMIN ---

# 3. CREAR UNA RESERVA (Vía API/Web)
@app.post("/reservar/", response_model=schemas.Turno)
def crear_reserva(turno: schemas.TurnoCreate, db: Session = Depends(get_db)):
    resultado = crud.create_turno(db=db, turno=turno)
    if resultado is None:
        raise HTTPException(status_code=400, detail="❌ Lo sentimos, ese horario ya está ocupado.")
    return resultado

# 4. CREAR SERVICIO
@app.post("/servicios/", response_model=schemas.Servicio)
def crear_servicio(servicio: schemas.ServicioCreate, db: Session = Depends(get_db)):
    nuevo_servicio = models.Servicio(
        negocio_id=1,
        nombre=servicio.nombre,
        duracion_minutos=servicio.duracion_minutos,
        precio=servicio.precio,
        activo=True
    )
    db.add(nuevo_servicio)
    db.commit()
    db.refresh(nuevo_servicio)
    return nuevo_servicio

# 5. CREAR STAFF
@app.post("/staff/", response_model=schemas.Staff)
def crear_staff(staff: schemas.StaffCreate, db: Session = Depends(get_db)):
    nuevo_staff = models.Staff(
        negocio_id=1,
        nombre=staff.nombre,
        telefono=staff.telefono,
        activo=True
    )
    db.add(nuevo_staff)
    db.commit()
    db.refresh(nuevo_staff)
    return nuevo_staff

# --- WHATSAPP (WEBHOOK REAL PARA TWILIO) ---
# Aquí es donde ocurre el cambio para arreglar el Error 422

# --- WEBHOOK INTELIGENTE V2 ---
@app.post("/webhook/")
async def recibir_mensaje(
    request: Request,
    Body: str = Form(...),
    From: str = Form(...),
    db: Session = Depends(get_db)
):
    telefono = From.replace("whatsapp:", "")
    texto_usuario = Body.lower().strip()
    cliente = crud.get_or_create_cliente(db, telefono)
    
    # 1. PRIORITY CHECK: ¿Está intentando reservar? (Detectamos formato "ID FECHA")
    if "-" in texto_usuario and ":" in texto_usuario:
        try:
            # Esperamos algo como: "1 2026-02-28 10:00"
            partes = texto_usuario.split(" ", 1)
            
            if len(partes) < 2:
                raise ValueError("Faltan datos")
                
            servicio_id_elegido = int(partes[0])
            fecha_texto = partes[1].strip()
            
            fecha_obj = datetime.strptime(fecha_texto, "%Y-%m-%d %H:%M")
            
            # Intentamos crear el turno (Staff ID 1 por defecto)
            turno_nuevo = schemas.TurnoCreate(
                negocio_id=1,
                staff_id=1, 
                servicio_id=servicio_id_elegido,
                telefono_cliente=telefono,
                nombre_cliente=cliente.nombre,
                fecha_hora_inicio=fecha_obj
            )
            
            resultado = crud.create_turno(db, turno_nuevo)
            
            if resultado:
                # Obtenemos los nombres reales para la respuesta
                nom_servicio = resultado.servicio.nombre 
                nom_barbero = resultado.staff.nombre # <--- ¡AQUÍ RESCATAMOS AL BARBERO! 💈
                
                respuesta = f"✅ *¡Reserva Confirmada!*\n\n" \
                            f"🗓 {fecha_texto}\n" \
                            f"✂ {nom_servicio}\n" \
                            f"💈 Profesional: {nom_barbero}\n\n" \
                            f"Te esperamos."
            else:
                respuesta = "❌ Ese horario ya está ocupado. Por favor elige otro."
                
        except ValueError:
            respuesta = "⚠ *Formato incorrecto.*\nPara reservar envía: ID FECHA HORA\nEjemplo: 1 2026-02-28 10:00"
        except Exception as e:
            respuesta = f"⚠ Error interno: {str(e)}"

    # 2. MENÚ: Saludo
    elif any(x in texto_usuario for x in ["hola", "buenas", "que tal", "qué tal", "como le va", "mbaeteko", "hi", "inicio"]):
        respuesta = f"¡Hola {cliente.nombre}! 👋 Bienvenido.\n" \
                    f"1️⃣ Ver Servicios\n" \
                    f"2️⃣ Mis Reservas"

    # 3. MENÚ: Servicios
    elif "1" in texto_usuario or "servicios" in texto_usuario:
        servicios = db.query(models.Servicio).filter(models.Servicio.activo == True).all()
        lista_texto = ""
        for s in servicios:
            lista_texto += f"[{s.id}] *{s.nombre}*: {int(s.precio)} Gs ({s.duracion_minutos} min)\n"
            
        respuesta = f"✂ *NUESTROS SERVICIOS*\n\n{lista_texto}\n" \
                    f"📢 *Para reservar, envía el número del servicio y la fecha.*\n" \
                    f"Ejemplo: *1 2026-02-28 10:00*"
    
    # 4. MENÚ: Mis Reservas
    elif "2" in texto_usuario or "mis reservas" in texto_usuario:
        # Lógica simple para ver reservas futuras del cliente
        turnos_cliente = db.query(models.Turno).filter(
            models.Turno.cliente_id == cliente.id,
            models.Turno.estado == "confirmado"
        ).all()
        
        if turnos_cliente:
            respuesta = "📂 *Tus Reservas Futuras:*\n"
            for t in turnos_cliente:
                respuesta += f"- {t.fecha_hora_inicio.strftime('%d/%m %H:%M')} ({t.servicio.nombre})\n"
        else:
            respuesta = "📂 No tienes reservas pendientes."

    else:
        # Solo responde el error si el mensaje parece un intento de comando fallido
        # Pero si es una charla normal, tratamos de ignorar o ser sutiles.
        
        # Para este MVP, te sugiero dejarlo así o poner:
        respuesta = "🤖 Soy el asistente virtual. Para reservar usa el menú di 'Hola'.\nSi estás hablando con el barbero, espera un momento y te responderá."

    # RESPUESTA TWILIO
    xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Message>{respuesta}</Message>
    </Response>"""
    return Response(content=xml_response, media_type="application/xml")

    # --- EN MAIN.PY (Agregar al final) ---

# 6. ACTUALIZAR SERVICIO (PUT)
@app.put("/servicios/{servicio_id}")
def actualizar_servicio(servicio_id: int, servicio_actualizado: schemas.ServicioCreate, db: Session = Depends(get_db)):
    db_servicio = db.query(models.Servicio).filter(models.Servicio.id == servicio_id).first()
    
    if db_servicio is None:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    # Actualizamos los campos
    db_servicio.nombre = servicio_actualizado.nombre
    db_servicio.precio = servicio_actualizado.precio
    db_servicio.duracion_minutos = servicio_actualizado.duracion_minutos
    
    db.commit()
    db.refresh(db_servicio)
    return db_servicio

# 7. ELIMINAR SERVICIO (DELETE)
@app.delete("/servicios/{servicio_id}")
def eliminar_servicio(servicio_id: int, db: Session = Depends(get_db)):
    db_servicio = db.query(models.Servicio).filter(models.Servicio.id == servicio_id).first()
    
    if db_servicio is None:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    # En lugar de borrarlo físicamente, lo desactivamos (Soft Delete) para no romper historicos
    # Pero como es un MVP y queremos borrar el error del precio, lo borramos de verdad:
    db.delete(db_servicio)
    db.commit()
    return {"mensaje": "Servicio eliminado"}


# --- EN MAIN.PY (Agregar al final) ---

# 8. ACTUALIZAR STAFF (PUT)
@app.put("/staff/{staff_id}")
def actualizar_staff(staff_id: int, staff_actualizado: schemas.StaffCreate, db: Session = Depends(get_db)):
    db_staff = db.query(models.Staff).filter(models.Staff.id == staff_id).first()
    
    if db_staff is None:
        raise HTTPException(status_code=404, detail="Staff no encontrado")
    
    # Actualizamos campos
    db_staff.nombre = staff_actualizado.nombre
    db_staff.telefono = staff_actualizado.telefono
    
    db.commit()
    db.refresh(db_staff)
    return db_staff

# 9. ELIMINAR STAFF (DELETE)
@app.delete("/staff/{staff_id}")
def eliminar_staff(staff_id: int, db: Session = Depends(get_db)):
    db_staff = db.query(models.Staff).filter(models.Staff.id == staff_id).first()
    
    if db_staff is None:
        raise HTTPException(status_code=404, detail="Staff no encontrado")
    
    # Borrado físico
    db.delete(db_staff)
    db.commit()
    return {"mensaje": "Staff eliminado"}

# --- EN MAIN.PY (Agregar al final) ---

# 10. LISTAR CLIENTES
@app.get("/clientes/", response_model=List[schemas.Cliente])
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(models.Cliente).all()

# 11. ACTUALIZAR CLIENTE (Para ponerle nombre real)
@app.put("/clientes/{cliente_id}")
def actualizar_cliente(cliente_id: int, cliente_data: schemas.ClienteCreate, db: Session = Depends(get_db)):
    db_cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if db_cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    db_cliente.nombre = cliente_data.nombre
    db_cliente.telefono = cliente_data.telefono_whatsapp
    # email opcional si lo tienes en el esquema, por ahora nombre y telefono bastan
    
    db.commit()
    db.refresh(db_cliente)
    return db_cliente
