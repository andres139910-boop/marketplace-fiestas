# -*- coding: utf-8 -*-
# seed.py — Agrega productos de ejemplo a la base de datos
from app import app, db
from database import Producto


with app.app_context():

    # ✅ FIX 2: synchronize_session evita advertencias en SQLAlchemy moderno
    Producto.query.delete(synchronize_session=False)
    db.session.commit()

    productos_ejemplo = [
        Producto(
            nombre="Globos Metálicos Dorados x20",
            descripcion="Globos metálicos de 12 pulgadas. Perfectos para decorar mesas y ambientes festivos.",
            precio=15000,
            categoria="globos",
            stock=100,
            imagen="globos.jpg"
        ),
        Producto(
            nombre="Piñata Estrella de 6 puntas",
            descripcion="Piñata tradicional de papel maché. Tamaño grande, ideal para niños.",
            precio=35000,
            categoria="pinatas",  # ✅ FIX 5: sin ñ para evitar encoding issues
            stock=25,
            imagen="pinata.jpg"
        ),
        Producto(
            nombre="Kit Decoración Jungle Party",
            descripcion="Set completo de decoración temática: guirnaldas, flores y follaje artificial.",
            precio=85000,
            categoria="decoracion",
            stock=15,
            imagen="jungle.jpg"
        ),
        Producto(
            nombre="Confeti y Serpentinas x5",
            descripcion="Pack variado de confeti de colores y serpentinas de papel. Ideal para cumpleaños.",
            precio=8000,
            categoria="confeti",
            stock=200,
            imagen="confeti.jpg"
        ),
        Producto(
            nombre="Vajilla Desechable 20 personas",
            descripcion="Set completo: platos, vasos y cubiertos decorativos para 20 personas.",
            precio=45000,
            categoria="vajilla",
            stock=50,
            imagen="vajilla.jpg"
        ),
        Producto(
            nombre="Arco de Globos Pastel",
            descripcion="Arco decorativo con globos en tonos pastel. Ideal para cumpleaños y baby showers.",
            precio=120000,
            categoria="globos",
            stock=10,
            imagen="arco_globos.jpg"
        ),
        Producto(
            nombre="Piñata Personaje Infantil",
            descripcion="Piñata temática personalizada con dulces incluidos. Perfecta para fiestas infantiles.",
            precio=60000,
            categoria="pinatas",  # ✅ FIX 5
            stock=12,
            imagen="pinata_personaje.jpg"
        ),
        Producto(
            nombre="Luces LED Decorativas x10m",
            descripcion="Tira de luces LED cálidas de 10 metros. Perfectas para ambientar eventos nocturnos.",
            precio=30000,
            categoria="decoracion",
            stock=40,
            imagen="luces_led.jpg"
        ),
        Producto(
            nombre="Mantel Temático Cumpleaños",
            descripcion="Mantel plástico decorativo resistente al agua. Diseño colorido para fiestas.",
            precio=18000,
            categoria="decoracion",
            stock=70,
            imagen="mantel.jpg"
        ),
        Producto(
            nombre="Sombreros de Fiesta x12",
            descripcion="Set de 12 sombreros festivos con diseños variados. Ajustables y coloridos.",
            precio=22000,
            categoria="accesorios",
            stock=90,
            imagen="sombreros.jpg"
        ),
    ]

    # ✅ FIX 3: Manejo de errores con rollback
    try:
        for p in productos_ejemplo:
            db.session.add(p)
        db.session.commit()
        print("✅ Productos de ejemplo agregados exitosamente.")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error al insertar productos: {e}")
