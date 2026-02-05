import streamlit as st
import pandas as pd
import requests
import time
import os
from database import SessionLocal
from models import Turno, Cliente, Staff, Servicio, Usuario

# Configuración de la página
st.set_page_config(page_title="Admin Barbería", layout="wide")

# Intenta leer la URL de las variables de entorno
API_URL = "https://barberia-bot-backend-1.onrender.com"
# --- GESTIÓN DE SESIÓN (LOGIN) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_nombre' not in st.session_state:
    st.session_state['user_nombre'] = ""

def login():
    col1, col2, col3 = st.columns([1,2,1])
    
    with col2:
        st.markdown("<h1 style='text-align: center;'>💈 Barber Admin</h1>", unsafe_allow_html=True)
        st.write("") 
        
        with st.form("login_form"):
            st.write("### Iniciar Sesión") 
            email = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            st.write("") 
            
            # CORREGIDO: Quitamos use_container_width para que no salga error rojo
            submit = st.form_submit_button("🔐 Entrar al Sistema")
            
            if submit:
                # 1. INTENTO DE ACCESO RÁPIDO (Backdoor para que no te quedes fuera)
                if email == "admin" and password == "1234":
                    st.session_state['logged_in'] = True
                    st.session_state['user_nombre'] = "Administrador"
                    st.success("¡Bienvenido Admin!")
                    st.rerun()
                
                # 2. INTENTO DE ACCESO POR BASE DE DATOS (Tu lógica original)
                try:
                    db = SessionLocal()
                    # Buscamos usuario en la BD (si existe la tabla y el usuario)
                    user = db.query(Usuario).filter(
                        Usuario.email == email, 
                        Usuario.password_hash == password
                    ).first()
                    db.close()
                    
                    if user:
                        st.session_state['logged_in'] = True
                        st.session_state['user_nombre'] = user.nombre
                        st.success(f"¡Bienvenido {user.nombre}!")
                        st.rerun()
                    else:
                        st.error("❌ Credenciales incorrectas")
                except Exception as e:
                    st.error(f"Error de conexión o tabla usuarios vacía: {e}")

# --- SI NO ESTÁ LOGUEADO, MOSTRAR LOGIN ---
if not st.session_state['logged_in']:
    login()
    st.stop()

# =========================================================
#  A PARTIR DE AQUÍ VA TU DASHBOARD (SOLO VISIBLE SI LOGUEADO)
# =========================================================

# Barra lateral con botón de Salir
with st.sidebar:
    st.write(f"Hola, **{st.session_state['user_nombre']}** 👋")
    if st.button("🔒 Cerrar Sesión"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.header("Menú Principal")
    opcion = st.radio("Ir a:", ["Dashboard", "Servicios", "Staff", "Clientes"])

# --- PÁGINA: DASHBOARD (TURNOS) ---
if opcion == "Dashboard":
    st.title("📅 Centro de Comando")
    
    col_btn, col_chk = st.columns([1, 3])
    with col_btn:
        if st.button("🔄 Refrescar"):
            st.rerun()
    with col_chk:
        ver_historial = st.checkbox("📜 Mostrar historial completo (Turnos pasados)", value=False)

    # 1. Diccionario para traducir meses a mano
    meses_es = {
        1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
    }

    db = SessionLocal()
    try:
        # Traemos todos los turnos
        turnos = db.query(Turno).all()
        
        if turnos:
            data = []
            for t in turnos:
                # Formateo de fecha
                dia = t.fecha_hora_inicio.day
                mes = meses_es[t.fecha_hora_inicio.month]
                anio = t.fecha_hora_inicio.year
                hora = t.fecha_hora_inicio.strftime("%H:%M")
                
                fecha_bonita = f"{dia} {mes} {anio}, {hora} hs"
                
                # Manejo de errores si se borró el cliente
                if t.cliente:
                    nombre_cli = t.cliente.nombre
                    tel_raw = t.cliente.telefono_whatsapp
                    tel_clean = tel_raw.replace("+", "").replace(" ", "")
                    link_wa = f"https://wa.me/{tel_clean}"
                else:
                    nombre_cli = "Desconocido"
                    link_wa = "#"

                estado_icon = "✅" if t.estado == "confirmado" else ("⏳" if t.estado == "pendiente" else "❌")
                
                data.append({
                    "ID": t.id,
                    "Fecha_Raw": t.fecha_hora_inicio,
                    "Fecha": fecha_bonita,
                    "Cliente": nombre_cli,
                    "Contacto": link_wa,
                    "Servicio": t.servicio.nombre if t.servicio else "N/A",
                    "Barbero": t.staff.nombre if t.staff else "N/A",
                    "Estado": f"{estado_icon} {t.estado.capitalize()}",
                    "Estado_Key": t.estado # Para filtrar fácil
                })
            
            df = pd.DataFrame(data)
            
            # Filtro de historial
            df["Fecha_Raw"] = pd.to_datetime(df["Fecha_Raw"])
            if not ver_historial:
                hoy = pd.Timestamp.now().normalize()
                df = df[df["Fecha_Raw"] >= hoy]
                
            df = df.sort_values(by="Fecha_Raw", ascending=True)

            # --- MÉTRICAS ---
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("📅 Turnos", len(df))
                col2.metric("✂ Servicios", df["Servicio"].nunique())
                col3.metric("⏳ Pendientes", len(df[df["Estado_Key"]=="pendiente"]))
                col4.metric("✅ Confirmados", len(df[df["Estado_Key"]=="confirmado"]))

            # --- TABLA ---
            st.write("### 📋 Agenda Detallada")
            if not df.empty:
                st.dataframe(
                    df,
                    column_order=("Fecha", "Cliente", "Servicio", "Barbero", "Estado", "Contacto"),
                    hide_index=True,
                    use_container_width=True, # Este sí funciona bien en dataframes
                    height=400,
                    column_config={
                        "Contacto": st.column_config.LinkColumn("Chat", display_text="💬 WhatsApp"),
                    }
                )
                
                # ========================================================
                # ZONA DE ACCIÓN: CONFIRMAR Y CANCELAR (ARREGLADA)
                # ========================================================
                st.divider()
                st.subheader("⚡ Gestión Rápida")

                # Filtramos las filas pendientes
                df_pendientes = df[df["Estado_Key"] == "pendiente"]
                
                if not df_pendientes.empty:
                    col_sel, col_btn_ok, col_btn_cancel = st.columns([2, 1, 1])
                    
                    with col_sel:
                        def formato_opcion(id_turno):
                            fila = df_pendientes[df_pendientes["ID"] == id_turno].iloc[0]
                            return f"{fila['Cliente']} - {fila['Fecha']}"

                        turno_id_to_edit = st.selectbox(
                            "Seleccionar Turno:", 
                            options=df_pendientes["ID"].tolist(),
                            format_func=formato_opcion
                        )

                    # --- BOTÓN CONFIRMAR ---
                    with col_btn_ok:
                        st.write("") 
                        st.write("") 
                        # key única y SIN use_container_width
                        if st.button("✅ Confirmar", key="btn_confirm_ok"):
                            turno_ok = db.query(Turno).filter(Turno.id == turno_id_to_edit).first()
                            if turno_ok:
                                turno_ok.estado = "confirmado"
                                db.commit()
                                st.toast("✅ Turno confirmado correctamente")
                                time.sleep(0.5)
                                st.rerun()

                    # --- BOTÓN CANCELAR (EL FIX DEFINITIVO) ---
                    with col_btn_cancel:
                        st.write("")
                        st.write("")
                        # key única, SIN use_container_width, type primary para rojo
                        if st.button("❌ Cancelar", type="primary", key="btn_cancel_fix"):
                            st.toast("⏳ Procesando...")
                            turno_cancel = db.query(Turno).filter(Turno.id == turno_id_to_edit).first()
                            
                            if turno_cancel:
                                turno_cancel.estado = "cancelado"
                                db.commit()
                                st.warning(f"Turno cancelado.") # Aviso visible
                                time.sleep(1) # Pausa dramática para leer
                                st.rerun() # Recarga obligatoria
                            else:
                                st.error("No se encontró el turno.")

                else:
                    st.info("👏 ¡Todo al día! No hay turnos pendientes.")
            else:
                st.info("No hay turnos para mostrar.")
        else:
            st.info("Aún no hay reservas en la base de datos.")
            
    except Exception as e:
        st.error(f"Error cargando turnos: {e}")
    finally:
        db.close()

# --- PÁGINA: SERVICIOS ---
elif opcion == "Servicios":
    st.subheader("🛠 Catálogo de Servicios")

    # 1. FORMULARIO CREAR
    with st.expander("➕ Crear Nuevo Servicio", expanded=False):
        with st.form("form_crear_servicio"):
            col1, col2 = st.columns(2)
            nombre_nuevo = col1.text_input("Nombre (ej: Barba Express)")
            precio_nuevo = col2.number_input("Precio (Gs)", min_value=0.0, step=5000.0)
            duracion_nuevo = st.slider("Duración (min)", 15, 120, 30, step=15)
            
            # Sin use_container_width
            if st.form_submit_button("Guardar Nuevo"):
                datos = {"nombre": nombre_nuevo, "precio": precio_nuevo, "duracion_minutos": duracion_nuevo, "activo": True}
                try:
                    res = requests.post(f"{API_URL}/servicios/", json=datos)
                    if res.status_code == 200:
                        st.success("✅ ¡Creado!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Error al guardar.")
                except Exception as e:
                    st.error(f"Error de conexión: {e}")

    # 2. LISTADO Y EDICIÓN
    st.write("---")
    st.subheader("📝 Gestión de Servicios")
    
    try:
        respuesta = requests.get(f"{API_URL}/servicios/")
        if respuesta.status_code == 200:
            lista_servicios = respuesta.json()
            
            if lista_servicios:
                col_tabla, col_edicion = st.columns([1, 1], gap="large")
                
                with col_tabla:
                    st.markdown("#### Listado")
                    df_servicios = pd.DataFrame(lista_servicios)
                    st.dataframe(df_servicios[["id", "nombre", "precio"]], hide_index=True, height=300)
                
                with col_edicion:
                    st.markdown("#### Editar Selección")
                    opciones = [f"{s['id']} - {s['nombre']}" for s in lista_servicios]
                    seleccion = st.selectbox("🔍 Buscar Servicio:", opciones)
                    
                    id_seleccionado = int(seleccion.split(" - ")[0])
                    servicio_actual = next((s for s in lista_servicios if s['id'] == id_seleccionado), None)
                    
                    if servicio_actual:
                        with st.container(border=True):
                            with st.form("form_editar_serv"):
                                nuevo_nombre = st.text_input("Nombre", value=servicio_actual['nombre'])
                                c1, c2 = st.columns(2)
                                nuevo_precio = c1.number_input("Precio", value=float(servicio_actual['precio']))
                                nueva_duracion = c2.number_input("Minutos", value=int(servicio_actual['duracion_minutos']))
                                
                                b1, b2 = st.columns(2)
                                if b1.form_submit_button("💾 Guardar"):
                                    datos_upd = {"nombre": nuevo_nombre, "precio": nuevo_precio, "duracion_minutos": nueva_duracion}
                                    requests.put(f"{API_URL}/servicios/{id_seleccionado}", json=datos_upd)
                                    st.success("Actualizado")
                                    st.rerun()
                                    
                                if b2.form_submit_button("🗑 Eliminar", type="primary"):
                                    requests.delete(f"{API_URL}/servicios/{id_seleccionado}")
                                    st.warning("Eliminado")
                                    time.sleep(1)
                                    st.rerun()
            else:
                st.info("No hay servicios.")
    except Exception as e:
        st.error(f"Error API: {e}")

# --- PÁGINA: STAFF ---
elif opcion == "Staff":
    st.subheader("👥 Gestión de Profesionales")
    
    with st.expander("➕ Agregar Nuevo Barbero", expanded=False):
        with st.form("form_crear_staff"):
            col1, col2 = st.columns(2)
            nombre_staff = col1.text_input("Nombre Completo")
            telefono_staff = col2.text_input("Teléfono")
            
            if st.form_submit_button("Guardar Nuevo"):
                datos_staff = {"nombre": nombre_staff, "telefono": telefono_staff, "negocio_id": 1, "activo": True}
                try:
                    res = requests.post(f"{API_URL}/staff/", json=datos_staff)
                    if res.status_code == 200:
                        st.success(f"✅ ¡{nombre_staff} agregado!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.write("---")
    try:
        respuesta = requests.get(f"{API_URL}/staff/")
        if respuesta.status_code == 200:
            staff_list = respuesta.json()
            if staff_list:
                col_tabla, col_edicion = st.columns([1, 1], gap="large")
                
                with col_tabla:
                    st.markdown("#### Listado")
                    df_staff = pd.DataFrame(staff_list)
                    st.dataframe(df_staff[["id", "nombre", "telefono"]], hide_index=True, height=300)
                
                with col_edicion:
                    st.markdown("#### Editar Selección")
                    opciones = [f"{s['id']} - {s['nombre']}" for s in staff_list]
                    seleccion = st.selectbox("🔍 Buscar Barbero:", opciones)
                    
                    id_seleccionado = int(seleccion.split(" - ")[0])
                    staff_actual = next((s for s in staff_list if s['id'] == id_seleccionado), None)
                    
                    if staff_actual:
                        with st.container(border=True):
                            with st.form("form_editar_staff"):
                                nuevo_nombre = st.text_input("Nombre", value=staff_actual['nombre'])
                                nuevo_telefono = st.text_input("Teléfono", value=staff_actual['telefono'])
                                
                                b1, b2 = st.columns(2)
                                if b1.form_submit_button("💾 Guardar"):
                                    datos_upd = {"nombre": nuevo_nombre, "telefono": nuevo_telefono}
                                    requests.put(f"{API_URL}/staff/{id_seleccionado}", json=datos_upd)
                                    st.success("Actualizado")
                                    st.rerun()
                                    
                                if b2.form_submit_button("🗑 Despedir", type="primary"):
                                    requests.delete(f"{API_URL}/staff/{id_seleccionado}")
                                    st.warning("Eliminado")
                                    time.sleep(1)
                                    st.rerun()
            else:
                st.info("Sin equipo.")
    except Exception as e:
        st.error(f"Error API: {e}")

# --- PÁGINA: CLIENTES ---
elif opcion == "Clientes":
    st.subheader("👤 Cartera de Clientes")
    st.write("Aquí puedes ponerle nombre real a los clientes que llegan desde WhatsApp.")

    try:
        respuesta = requests.get(f"{API_URL}/clientes/")
        if respuesta.status_code == 200:
            lista_clientes = respuesta.json()
            
            if lista_clientes:
                col_tabla, col_edicion = st.columns([1, 1], gap="large")
                
                with col_tabla:
                    st.markdown("#### Listado")
                    df = pd.DataFrame(lista_clientes)
                    st.dataframe(df[["id", "nombre", "telefono_whatsapp"]], hide_index=True, height=400)
                
                with col_edicion:
                    st.markdown("#### Editar Cliente")
                    opciones = [f"{c['id']} - {c['nombre']} ({c['telefono_whatsapp']})" for c in lista_clientes]
                    seleccion = st.selectbox("Buscar Cliente:", opciones)
                    
                    id_selec = int(seleccion.split(" - ")[0])
                    cliente_actual = next((c for c in lista_clientes if c['id'] == id_selec), None)
                    
                    if cliente_actual:
                        with st.container(border=True):
                            with st.form("form_cliente"):
                                st.info(f"Editando: {cliente_actual['telefono_whatsapp']}")
                                nuevo_nombre = st.text_input("Nombre Real", value=cliente_actual['nombre'])
                                nuevo_telefono = st.text_input("Teléfono", value=cliente_actual['telefono_whatsapp'], disabled=True)
                                
                                if st.form_submit_button("💾 Guardar Nombre"):
                                    datos = {
                                        "nombre": nuevo_nombre,
                                        "telefono_whatsapp": nuevo_telefono,
                                        "email": ""
                                    }
                                    res = requests.put(f"{API_URL}/clientes/{id_selec}", json=datos)
                                    if res.status_code == 200:
                                        st.success("¡Nombre actualizado!")
                                        st.rerun()
                                    else:
                                        st.error("Error al actualizar.")
            else:
                st.info("Aún no hay clientes.")
    except Exception as e:
        st.error(f"Error de conexión: {e}")