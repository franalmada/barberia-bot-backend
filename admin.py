import streamlit as st
import pandas as pd
import requests

# Configuración de la página
st.set_page_config(page_title="Admin Barbería", layout="wide")

API_URL = "http://127.0.0.1:8000"

# --- GESTIÓN DE SESIÓN (LOGIN) ---
# --- GESTIÓN DE SESIÓN (LOGIN) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def login():
    # Usamos columnas para centrar todo
    col1, col2, col3 = st.columns([1,2,1])
    
    with col2:
        # Título centrado
        st.markdown("<h1 style='text-align: center;'>💈 Barber Admin</h1>", unsafe_allow_html=True)
        st.write("") # Espacio
        
        with st.form("login_form"):
            st.write("### Iniciar Sesión") # Subtítulo dentro de la caja
            email = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            
            st.write("") # Espacio para separar botón
            
            # Botón que ocupa todo el ancho del formulario
            submit = st.form_submit_button("🔐 Entrar al Sistema", use_container_width=True)
            
            if submit:
                # AQUÍ TU LÓGICA DE BASE DE DATOS (La que ya tienes está perfecta)
                from database import SessionLocal
                from models import Usuario
                
                db = SessionLocal()
                # Nota: Asegúrate de tener usuarios cargados en tu tabla 'usuarios'
                user = db.query(Usuario).filter(
                    Usuario.email == email, 
                    Usuario.password_hash == password
                ).first()
                db.close()
                
                if user:
                    st.session_state['logged_in'] = True
                    st.session_state['user_nombre'] = user.nombre
                    st.success("¡Bienvenido!")
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")

# --- SI NO ESTÁ LOGUEADO, MOSTRAR LOGIN ---
if not st.session_state['logged_in']:
    login()
    st.stop()

# =========================================================
#  A PARTIR DE AQUÍ VA TU DASHBOARD (SOLO VISIBLE SI LOGUEADO)
# =========================================================

# Barra lateral con botón de Salir
st.sidebar.write(f"Hola, **{st.session_state['user_nombre']}** 👋")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state['logged_in'] = False
    st.rerun()

st.sidebar.header("Menú Principal")

opcion = st.sidebar.radio("Ir a:", ["Dashboard", "Servicios", "Staff", "Clientes"])

st.title("💈 Panel de Control - Barbería")

# --- PÁGINA: DASHBOARD ---
# --- EN ADMIN.PY (Sección Dashboard Ajustada ---

if opcion == "Dashboard":
    st.subheader("📅 Centro de Comando")
    
    col_btn, col_chk = st.columns([1, 3])
    with col_btn:
        if st.button("🔄 Refrescar", use_container_width=True):
            st.rerun()
    with col_chk:
        ver_historial = st.checkbox("📜 Mostrar historial completo (Turnos pasados)", value=False)

    from database import SessionLocal
    from models import Turno
    import pandas as pd
    
    # 1. Diccionario para traducir meses a mano (Solución a prueba de balas)
    meses_es = {
        1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
    }

    db = SessionLocal()
    turnos = db.query(Turno).all()
    
    if turnos:
        data = []
        for t in turnos:
            # --- FORMATEO MANUAL DE FECHA EN ESPAÑOL ---
            # Extraemos día, mes y hora del objeto fecha
            dia = t.fecha_hora_inicio.day
            mes = meses_es[t.fecha_hora_inicio.month] # Usamos nuestro diccionario
            anio = t.fecha_hora_inicio.year
            hora = t.fecha_hora_inicio.strftime("%H:%M") # Hora simple (ej: 14:30)
            
            # Creamos el texto final: "28 Feb 2026, 14:30"
            fecha_bonita = f"{dia} {mes} {anio}, {hora} hs"
            
            # -------------------------------------------

            telefono_limpio = t.cliente.telefono_whatsapp.replace("+", "").replace(" ", "")
            link_wa = f"https://wa.me/{telefono_limpio}"
            estado_icon = "✅ Confirmado" if t.estado == "confirmado" else "⏳ Pendiente"
            
            data.append({
                "ID": t.id,
                "Fecha_Raw": t.fecha_hora_inicio, # Guardamos la original oculta para filtrar
                "Fecha": fecha_bonita,            # Esta es la que mostramos
                "Cliente": t.cliente.nombre,
                "Contacto": link_wa,
                "Servicio": t.servicio.nombre,
                "Barbero": t.staff.nombre,
                "Estado": estado_icon
            })
        
        df = pd.DataFrame(data)
        
        # Filtramos usando la fecha original (Fecha_Raw) que es numérica
        df["Fecha_Raw"] = pd.to_datetime(df["Fecha_Raw"])
        
        if not ver_historial:
            hoy = pd.Timestamp.now().normalize()
            df = df[df["Fecha_Raw"] >= hoy]
            
        # Ordenamos por fecha real (para que no ordene alfabéticamente los textos)
        df = df.sort_values(by="Fecha_Raw", ascending=True)

        # --- MÉTRICAS ---
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📅 Turnos", len(df))
            col2.metric("✂ Servicios", df["Servicio"].nunique())
            col3.metric("⏳ Pendientes", len(df[df["Estado"]=="⏳ Pendiente"]))
            col4.metric("✅ Confirmados", len(df[df["Estado"]=="✅ Confirmado"]))

        # --- TABLA ---
        st.write("### 📋 Agenda Detallada")
        
        st.dataframe(
            df,
            # Quitamos "Fecha_Raw" de aquí para que no se vea, mostramos "Fecha" (la bonita)
            column_order=("Fecha", "Cliente", "Servicio", "Barbero", "Estado", "Contacto"),
            hide_index=True,
            use_container_width=True,
            height=400,
            column_config={
                "Fecha": st.column_config.TextColumn(
                    "Fecha y Hora",
                    width="medium"
                ),
                "Contacto": st.column_config.LinkColumn(
                    "WhatsApp",
                    display_text="💬 Chatear"
                ),
                "Estado": st.column_config.TextColumn(
                    "Estado",
                    width="small"
                )
            }
        )
        
    else:
        st.info("😴 No hay turnos registrados.")
    
    db.close()
# --- PÁGINA: SERVICIOS ---
elif opcion == "Servicios":
    st.subheader("🛠 Catálogo de Servicios")

    # 1. FORMULARIO DE CREACIÓN (Igual que antes, lo ponemos en un expander para ahorrar espacio)
    with st.expander("➕ Crear Nuevo Servicio", expanded=False):
        with st.form("form_crear_servicio"):
            col1, col2 = st.columns(2)
            nombre_nuevo = col1.text_input("Nombre (ej: Barba Express)")
            precio_nuevo = col2.number_input("Precio (Gs)", min_value=0.0, step=5000.0)
            duracion_nuevo = st.slider("Duración (min)", 15, 120, 30, step=15)
            
            if st.form_submit_button("Guardar Nuevo"):
                datos = {"nombre": nombre_nuevo, "precio": precio_nuevo, "duracion_minutos": duracion_nuevo}
                try:
                    res = requests.post(f"{API_URL}/servicios/", json=datos)
                    if res.status_code == 200:
                        st.success("✅ ¡Creado!")
                        # Un pequeño truco: espera 1 seg para que el usuario lea el mensaje antes de recargar
                        import time
                        time.sleep(1) 
                        st.rerun()
                    else:
                        st.error("Error al guardar en el servidor.")
                except Exception as e: # <--- AQUÍ ESTÁ LA CLAVE: "Exception"
                    st.error(f"Error de conexión: {e}")

    # 2. LISTADO Y EDICIÓN
    # ... (La parte 1 del "Formulario de Creación" déjala igual) ...

    # 2. LISTADO Y EDICIÓN
    st.write("---")
    st.subheader("📝 Gestión de Servicios")
    
    try:
        respuesta = requests.get(f"{API_URL}/servicios/")
        if respuesta.status_code == 200:
            lista_servicios = respuesta.json()
            
            if lista_servicios:
                # --- NUEVO DISEÑO DE COLUMNAS ---
                col_tabla, col_edicion = st.columns([1, 1], gap="large")
                
                with col_tabla:
                    st.markdown("#### 1. Listado")
                    # Mostramos una tabla más compacta
                    df_servicios = pd.DataFrame(lista_servicios)
                    st.dataframe(
                        df_servicios[["id", "nombre", "precio"]], 
                        use_container_width=True, 
                        hide_index=True,
                        height=300 # Altura fija para que se vea prolijo
                    )
                
                with col_edicion:
                    st.markdown("#### 2. Editar Selección")
                    
                    # Selector
                    opciones = [f"{s['id']} - {s['nombre']}" for s in lista_servicios]
                    seleccion = st.selectbox("🔍 Buscar Servicio a editar:", opciones)
                    
                    # Identificamos el ID
                    id_seleccionado = int(seleccion.split(" - ")[0])
                    servicio_actual = next((s for s in lista_servicios if s['id'] == id_seleccionado), None)
                    
                    if servicio_actual:
                        # Ponemos el formulario dentro de un contenedor con borde para resaltarlo
                        with st.container(border=True):
                            with st.form("form_editar"):
                                st.caption(f"Editando ID: {id_seleccionado}")
                                
                                nuevo_nombre = st.text_input("Nombre", value=servicio_actual['nombre'])
                                # Usamos columnas dentro del formulario para ahorrar espacio vertical
                                c1, c2 = st.columns(2)
                                nuevo_precio = c1.number_input("Precio", value=float(servicio_actual['precio']), step=5000.0)
                                nueva_duracion = c2.number_input("Minutos", value=int(servicio_actual['duracion_minutos']))
                                
                                st.write("") # Espacio
                                
                                # Botones de acción
                                b1, b2 = st.columns(2)
                                boton_actualizar = b1.form_submit_button("💾 Guardar", use_container_width=True)
                                boton_borrar = b2.form_submit_button("🗑 Eliminar", type="primary", use_container_width=True)
                                
                                if boton_actualizar:
                                    datos_upd = {
                                        "nombre": nuevo_nombre, 
                                        "precio": nuevo_precio, 
                                        "duracion_minutos": nueva_duracion
                                    }
                                    res = requests.put(f"{API_URL}/servicios/{id_seleccionado}", json=datos_upd)
                                    if res.status_code == 200:
                                        st.success("¡Actualizado!")
                                        st.rerun()
                                    else:
                                        st.error("Error al actualizar.")
                                        
                                if boton_borrar:
                                    res = requests.delete(f"{API_URL}/servicios/{id_seleccionado}")
                                    if res.status_code == 200:
                                        st.warning("¡Eliminado!")
                                        st.rerun()
                                    else:
                                        st.error("Error al borrar.")
            else:
                st.info("No hay servicios cargados.")
    except Exception as e:
        st.error(f"Error conectando con API: {e}")

# --- PÁGINA: STAFF ---
# --- EN ADMIN.PY (Reemplazar toda la sección Staff) ---

elif opcion == "Staff":
    st.subheader("👥 Gestión de Profesionales")
    
    # 1. FORMULARIO DE CREACIÓN (Expander)
    with st.expander("➕ Agregar Nuevo Barbero", expanded=False):
        with st.form("form_crear_staff"):
            col1, col2 = st.columns(2)
            nombre_staff = col1.text_input("Nombre Completo")
            telefono_staff = col2.text_input("Teléfono (sin espacios)")
            
            submitted_staff = st.form_submit_button("Guardar Nuevo")
            
            if submitted_staff:
                datos_staff = {"nombre": nombre_staff, "telefono": telefono_staff}
                try:
                    res = requests.post(f"{API_URL}/staff/", json=datos_staff)
                    if res.status_code == 200:
                        st.success(f"✅ ¡{nombre_staff} agregado!")
                        st.rerun()
                    else:
                        st.error("Error al guardar.")
                except Exception as e:
                    st.error("Error de conexión.")

    # 2. LISTADO Y EDICIÓN (Diseño Split View)
    st.write("---")
    st.write("📝 **Gestionar Equipo**")

    try:
        respuesta = requests.get(f"{API_URL}/staff/")
        if respuesta.status_code == 200:
            staff_list = respuesta.json()
            if staff_list:
                col_tabla, col_edicion = st.columns([1, 1], gap="large")
                
                # COLUMNA IZQUIERDA: LISTADO
                with col_tabla:
                    st.markdown("#### 1. Listado")
                    df_staff = pd.DataFrame(staff_list)
                    st.dataframe(
                        df_staff[["id", "nombre", "telefono"]], 
                        use_container_width=True,
                        hide_index=True,
                        height=300
                    )
                
                # COLUMNA DERECHA: EDICIÓN
                with col_edicion:
                    st.markdown("#### 2. Editar Selección")
                    
                    opciones = [f"{s['id']} - {s['nombre']}" for s in staff_list]
                    seleccion = st.selectbox("🔍 Buscar Barbero:", opciones)
                    
                    id_seleccionado = int(seleccion.split(" - ")[0])
                    staff_actual = next((s for s in staff_list if s['id'] == id_seleccionado), None)
                    
                    if staff_actual:
                        with st.container(border=True):
                            with st.form("form_editar_staff"):
                                st.caption(f"Editando ID: {id_seleccionado}")
                                
                                nuevo_nombre = st.text_input("Nombre", value=staff_actual['nombre'])
                                nuevo_telefono = st.text_input("Teléfono", value=staff_actual['telefono'])
                                
                                st.write("")
                                
                                b1, b2 = st.columns(2)
                                btn_update = b1.form_submit_button("💾 Guardar", use_container_width=True)
                                btn_delete = b2.form_submit_button("🗑 Despedir", type="primary", use_container_width=True)
                                
                                if btn_update:
                                    datos_upd = {"nombre": nuevo_nombre, "telefono": nuevo_telefono}
                                    res = requests.put(f"{API_URL}/staff/{id_seleccionado}", json=datos_upd)
                                    if res.status_code == 200:
                                        st.success("¡Datos actualizados!")
                                        st.rerun()
                                    else:
                                        st.error("No se pudo actualizar.")
                                        
                                if btn_delete:
                                    # Opcional: Podríamos verificar si tiene turnos futuros antes de borrar,
                                    # pero para el MVP permitimos borrar directo.
                                    res = requests.delete(f"{API_URL}/staff/{id_seleccionado}")
                                    if res.status_code == 200:
                                        st.warning("¡Barbero eliminado del sistema!")
                                        st.rerun()
                                    else:
                                        st.error("No se pudo borrar.")
            else:
                st.info("Aún no tienes equipo registrado.")
    except Exception as e:
        st.error(f"Error API: {e}")

        # --- EN ADMIN.PY (Agregar al final del archivo) ---

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
                    # Mostramos ID, Nombre y Telefono
                    st.dataframe(
                        df[["id", "nombre", "telefono_whatsapp"]], 
                        use_container_width=True, 
                        hide_index=True,
                        height=400
                    )
                
                with col_edicion:
                    st.markdown("#### Editar Cliente")
                    
                    # El selector muestra: ID - Nombre (Teléfono)
                    opciones = [f"{c['id']} - {c['nombre']} ({c['telefono_whatsapp']})" for c in lista_clientes]
                    seleccion = st.selectbox("Buscar Cliente:", opciones)
                    
                    id_selec = int(seleccion.split(" - ")[0])
                    cliente_actual = next((c for c in lista_clientes if c['id'] == id_selec), None)
                    
                    if cliente_actual:
                        with st.container(border=True):
                            with st.form("form_cliente"):
                                st.info(f"Editando a: {cliente_actual['telefono_whatsapp']}")
                                
                                # Aquí es donde el barbero corrige el "Sin Nombre"
                                nuevo_nombre = st.text_input("Nombre Real", value=cliente_actual['nombre'])
                                
                                # El teléfono usualmente no se toca porque es su ID de WhatsApp, pero lo dejamos visible
                                nuevo_telefono = st.text_input("Teléfono", value=cliente_actual['telefono_whatsapp'], disabled=True)
                                
                                if st.form_submit_button("💾 Guardar Nombre Real"):
                                    datos = {
                                        "nombre": nuevo_nombre,
                                        "telefono_whatsapp": nuevo_telefono,
                                        "email": "" # Campo dummy si el schema lo pide
                                    }
                                    res = requests.put(f"{API_URL}/clientes/{id_selec}", json=datos)
                                    if res.status_code == 200:
                                        st.success("¡Nombre actualizado!")
                                        st.rerun()
                                    else:
                                        st.error("Error al actualizar.")
            else:
                st.info("Aún no hay clientes registrados.")
    except Exception as e:
        st.error(f"Error de conexión: {e}")