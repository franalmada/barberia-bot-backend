from database import engine, Base, SessionLocal
from models import Usuario, Negocio, Staff, Servicio, Cliente
import models 

def inicializar_sistema():
    print("🏗️ Creando tablas en Neon Postgres...")
    # Esto crea las tablas si no existen
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # 1. Verificar si ya existe el negocio
        negocio = db.query(Negocio).first()
        if not negocio:
            print("🏢 Creando negocio inicial...")
            negocio = Negocio(
                nombre="Barbería Central",
                telefono_contacto="+595981000000",
                activo=True
            )
            db.add(negocio)
            db.commit()
            db.refresh(negocio)

        # 2. Verificar si ya existe el administrador
        admin = db.query(Usuario).filter(Usuario.email == "admin@barberia.com").first()
        if not admin:
            print("👤 Creando cuenta de administrador...")
            admin = Usuario(
                negocio_id=negocio.id,
                email="admin@barberia.com",
                password_hash="admin123", # Nota: En producción usa hashing
                rol="admin",
                nombre="Admin Principal"
            )
            db.add(admin)

        # 3. Crear un Barbero por defecto (Staff)
        if db.query(Staff).count() == 0:
            print("💈 Creando barbero inicial...")
            barbero = Staff(
                negocio_id=negocio.id,
                nombre="Barbero 1",
                telefono="+595991000000",
                activo=True
            )
            db.add(barbero)

        # 4. Crear un Servicio de prueba
        if db.query(Servicio).count() == 0:
            print("✂️ Creando servicio de prueba...")
            servicio = Servicio(
                negocio_id=negocio.id,
                nombre="Corte Clásico",
                duracion_minutos=30,
                precio=50000.00,
                activo=True
            )
            db.add(servicio)

        db.commit()
        print("✅ ¡Sistema inicializado con éxito en la nube!")

    except Exception as e:
        print(f"❌ Error durante la inicialización: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    inicializar_sistema()