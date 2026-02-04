import streamlit as st
from datetime import datetime, timedelta, time
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Servicio, Staff, Turno, Cliente, Negocio

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Reserva tu Turno", page_icon="💈", layout="centered")

# --- ESTILOS CSS PARA QUE SE VEA BIEN EN MÓVIL ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #FF4B4B;
        color: white;
        font-weight: bold;
        border-radius: 10px;
        height: 50px;
    }
    .stSelectbox, .stDateInput {
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE BASE DE DATOS ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def obtener_horarios_disponibles(db: Session, fecha_elegida, staff_id, duracion_servicio):
    # 1. Definir horario laboral (Ej: 09:00 a 20:00)
    hora_apertura = time(9, 0)
    hora_cierre = time(20, 0)
    
    # 2. Generar todos los bloques posibles cada 30 min
    bloques = []
    tiempo_actual = datetime.combine(fecha_elegida, hora_apertura)
    tiempo_cierre = datetime.combine(fecha_elegida, hora_cierre)
    
    while tiempo_actual + timedelta(minutes=duracion_servicio) <= tiempo_cierre:
        bloques.append(tiempo_actual)
        tiempo_actual += timedelta(minutes=30) # Intervalo entre turnos
    
    # 3. Buscar turnos ya ocupados en ese día y staff
    turnos_ocupados = db.query(Turno).filter(
        Turno.staff_id == staff_id,
        Turno.estado != 'cancelado'
        # Aquí simplificamos: traemos todo el día. En prod filtrarías por fecha exacta.
    ).all()
    
    # Filtramos en Python para asegurar la fecha (Postgres a veces es quisquilloso con formatos)
    turnos_ocupados = [t for t in turnos_ocupados if t.fecha_hora_inicio.date() == fecha_elegida]

    # 4. Restar los ocupados
    horarios_libres = []
    for bloque in bloques:
        ocupado = False
        fin_bloque = bloque + timedelta(minutes=duracion_servicio)
        
        for turno in turnos_ocupados:
            # Si el bloque se solapa con un turno existente
            inicio_t = turno.fecha_hora_inicio
            fin_t = turno.fecha_hora_fin
            
            # Lógica de colisión de horarios
            if (bloque < fin_t) and (fin_bloque > inicio_t):
                ocupado = True
                break
        
        if not ocupado:
            horarios_libres.append(bloque.strftime("%H:%M"))
            
    return horarios_libres

# --- INTERFAZ PRINCIPAL ---
def main():
    db = next(get_db())
    
    # Encabezado
    st.image("https://cdn-icons-png.flaticon.com/512/3652/3652191.png", width=80)
 # Icono genérico o logo
    st.title("Barbería Central")
    st.write("Reserva tu turno en segundos.")
    st.divider()

    # 1. PASO 1: SELECCIONAR SERVICIO
    servicios = db.query(Servicio).filter(Servicio.activo == True).all()
    nombres_servicios = [f"{s.nombre} - {int(s.precio):,} Gs" for s in servicios]
    
    servicio_elegido_nombre = st.selectbox("1. ¿Qué te hacemos hoy?", nombres_servicios)
    
    # Encontrar el objeto servicio seleccionado
    index = nombres_servicios.index(servicio_elegido_nombre)
    servicio_obj = servicios[index]

    # 2. PASO 2: SELECCIONAR BARBERO
    barberos = db.query(Staff).filter(Staff.activo == True).all()
    
    if not barberos:
        st.error("⚠️ No hay profesionales disponibles en este momento. Por favor contacta al administrador.")
        st.stop() # Detiene la ejecución aquí para no generar error
        
    nombres_barberos = [b.nombre for b in barberos]
    barbero_elegido_nombre = st.selectbox("2. ¿Con quién?", nombres_barberos)
    
    # Buscamos el objeto completo basado en el nombre seleccionado
    # (Ahora es seguro hacerlo porque validamos que la lista no está vacía)
    barbero_obj = next((b for b in barberos if b.nombre == barbero_elegido_nombre), None)

    # 3. PASO 3: FECHA Y HORA
    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input("3. Elige el día", min_value=datetime.today())
    
    # Calcular horas libres dinámicamente
    horarios = obtener_horarios_disponibles(db, fecha, barbero_obj.id, servicio_obj.duracion_minutos)
    
    with col2:
        if not horarios:
            st.error("Agenda llena.")
            hora = None
        else:
            hora = st.selectbox("Horarios libres", horarios)

    st.divider()

    # 4. PASO 4: DATOS DEL CLIENTE
    st.write("👤 **Tus Datos**")
    nombre_cliente = st.text_input("Nombre y Apellido")
    celular_cliente = st.text_input("WhatsApp (Ej: 0981...)", help="Sin espacios ni guiones")

    # BOTÓN DE CONFIRMACIÓN
    if st.button("CONFIRMAR RESERVA ✅"):
        if not nombre_cliente or not celular_cliente or not hora:
            st.warning("Por favor completa todos los datos.")
        else:
            try:
                # A. Buscar o Crear Cliente
                cliente = db.query(Cliente).filter(Cliente.telefono_whatsapp == celular_cliente).first()
                if not cliente:
                    cliente = Cliente(
                        negocio_id=servicio_obj.negocio_id,
                        nombre=nombre_cliente,
                        telefono_whatsapp=celular_cliente
                    )
                    db.add(cliente)
                    db.commit()
                    db.refresh(cliente)

                # B. Crear el Turno
                fecha_hora_str = f"{fecha} {hora}"
                inicio = datetime.strptime(fecha_hora_str, "%Y-%m-%d %H:%M")
                fin = inicio + timedelta(minutes=servicio_obj.duracion_minutos)

                nuevo_turno = Turno(
                    negocio_id=servicio_obj.negocio_id,
                    staff_id=barbero_obj.id,
                    cliente_id=cliente.id,
                    servicio_id=servicio_obj.id,
                    fecha_hora_inicio=inicio,
                    fecha_hora_fin=fin,
                    estado="pendiente",
                    origen="web_cliente",
                    notas="Reserva desde Web App"
                )
                db.add(nuevo_turno)
                db.commit()

                # C. Feedback y Link a WhatsApp
                st.balloons()
                st.success(f"¡Listo {nombre_cliente}! Turno agendado.")
                
                # Mensaje pre-llenado para enviar al dueño
                msg_wa = f"Hola, soy {nombre_cliente}. Acabo de reservar turno para *{servicio_obj.nombre}* el día {fecha} a las {hora}. ¿Me confirmas?"
                link_wa = f"https://wa.me/595981000000?text={msg_wa.replace(' ', '%20')}" # CAMBIA ESTE NUMERO POR EL DEL BARBERO
                
                st.markdown(f"""
                <a href="{link_wa}" target="_blank">
                    <button style="background-color:#25D366; color:white; border:none; padding:15px 32px; text-align:center; text-decoration:none; display:inline-block; font-size:16px; margin:4px 2px; cursor:pointer; border-radius:12px; width:100%;">
                        📱 Enviar comprobante por WhatsApp
                    </button>
                </a>
                """, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Ocurrió un error: {e}")
                db.rollback()

if __name__ == "__main__":
    main()