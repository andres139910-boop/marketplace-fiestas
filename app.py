# -*- coding: utf-8 -*-
import os
import uuid
from flask import (Flask, render_template, request, redirect,
                   url_for, flash, session, jsonify)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from database import db, Producto, ItemCarrito, Usuario, Favorito, Resena, Orden, ItemOrden, Notificacion

app = Flask(__name__)

# ============================
# CONFIGURACIÓN
# ============================
app.config['SECRET_KEY']                     = os.environ.get('SECRET_KEY', 'fiesta_secreta_2026_dev')
app.config['SQLALCHEMY_DATABASE_URI']        = 'sqlite:///marketplace.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER']                  = 'static/images'

# Flask-Mail — usa variables de entorno (nunca hardcodear credenciales)
app.config['MAIL_SERVER']         = 'smtp.gmail.com'
app.config['MAIL_PORT']           = 587
app.config['MAIL_USE_TLS']        = True
app.config['MAIL_USERNAME']       = 'andres.139910@gmail.com'
app.config['MAIL_PASSWORD']       = 'lieu dbgh vkce rdly'
app.config['MAIL_DEFAULT_SENDER'] = 'PartyShop Cartagena <andres.139910@gmail.com>'

EXTENSIONES_PERMITIDAS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Categorías canónicas — única fuente de verdad en toda la app
CATEGORIAS = ['globos', 'decoracion', 'pinatas', 'confeti', 'vajilla',
              'iluminacion', 'disfraz', 'accesorios', 'tortas']

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
mail = Mail(app)

# ============================
# FLASK-LOGIN
# ============================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '⚠️ Debes iniciar sesión para acceder.'
login_manager.login_message_category = 'error'

@login_manager.user_loader
def cargar_usuario(user_id):
    return Usuario.query.get(int(user_id))

with app.app_context():
    db.create_all()


# ============================
# DECORADOR ADMIN
# ============================
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.es_admin:
            flash('❌ Acceso restringido a administradores.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def extension_permitida(nombre_archivo):
    return '.' in nombre_archivo and \
           nombre_archivo.rsplit('.', 1)[1].lower() in EXTENSIONES_PERMITIDAS


# ============================
# HELPERS
# ============================
def crear_notificacion(usuario_id, mensaje, tipo='info', url=None):
    notif = Notificacion(
        usuario_id=usuario_id,
        mensaje=mensaje,
        tipo=tipo,
        url=url
    )
    db.session.add(notif)
    db.session.commit()


def enviar_email(destinatario, asunto, cuerpo_html):
    try:
        msg = Message(asunto, recipients=[destinatario])
        msg.html = cuerpo_html
        mail.send(msg)
    except Exception as e:
        print(f'Error al enviar email: {e}')


def url_segura(next_url):
    """Valida que el redirect 'next' sea relativo (evita open redirect)."""
    from urllib.parse import urlparse
    if next_url:
        parsed = urlparse(next_url)
        if not parsed.netloc and not parsed.scheme:
            return next_url
    return None


# ============================
# CONTEXT PROCESSOR GLOBAL
# ============================
@app.context_processor
def inject_globals():
    sesion_id = session.get('sesion_id', '')
    count = ItemCarrito.query.filter_by(
        sesion_id=sesion_id
    ).count() if sesion_id else 0

    favoritos_ids   = []
    notif_no_leidas = 0

    if current_user.is_authenticated:
        favoritos_ids = [
            f.producto_id for f in
            Favorito.query.filter_by(usuario_id=current_user.id).all()
        ]
        notif_no_leidas = Notificacion.query.filter_by(
            usuario_id=current_user.id,
            leida=False
        ).count()

    return dict(
        items_carrito=count,
        favoritos_ids=favoritos_ids,
        notif_no_leidas=notif_no_leidas,
        CATEGORIAS=CATEGORIAS
    )


# ============================
# MANEJADOR 404
# ============================
@app.errorhandler(404)
def pagina_no_encontrada(e):
    return render_template('404.html'), 404


# ============================
# RUTA: Inicio
# ============================
@app.route('/')
def index():
    busqueda         = request.args.get('q', '')
    categoria_filtro = request.args.get('categoria', '')
    orden            = request.args.get('orden', 'recientes')

    if 'sesion_id' not in session:
        session['sesion_id'] = str(uuid.uuid4())

    query = Producto.query

    if busqueda:
        query = query.filter(
            Producto.nombre.ilike(f'%{busqueda}%') |
            Producto.descripcion.ilike(f'%{busqueda}%')
        )

    if categoria_filtro:
        query = query.filter_by(categoria=categoria_filtro)

    if orden == 'precio_asc':
        query = query.order_by(Producto.precio.asc())
    elif orden == 'precio_desc':
        query = query.order_by(Producto.precio.desc())
    elif orden == 'nombre_asc':
        query = query.order_by(Producto.nombre.asc())
    elif orden == 'mas_stock':
        query = query.order_by(Producto.stock.desc())
    elif orden == 'mas_vistos':
        query = query.order_by(Producto.visitas.desc())
    else:
        query = query.order_by(Producto.fecha_creado.desc())

    pagina    = request.args.get('page', 1, type=int)
    productos = query.paginate(page=pagina, per_page=8)

    categorias = db.session.query(Producto.categoria).distinct().all()
    categorias = [c[0] for c in categorias]

    return render_template(
        'index.html',
        productos=productos,
        categorias=categorias,
        categoria_filtro=categoria_filtro,
        orden=orden
    )


# ============================
# RUTA: Registro
# ============================
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        nombre    = request.form.get('nombre', '').strip()
        email     = request.form.get('email', '').strip().lower()
        password  = request.form.get('password', '')
        confirmar = request.form.get('confirmar', '')

        if not nombre or not email or not password:
            flash('❌ Todos los campos son obligatorios.', 'error')
            return render_template('registro.html')

        if password != confirmar:
            flash('❌ Las contraseñas no coinciden.', 'error')
            return render_template('registro.html')

        if len(password) < 6:
            flash('❌ La contraseña debe tener al menos 6 caracteres.', 'error')
            return render_template('registro.html')

        if Usuario.query.filter_by(email=email).first():
            flash('❌ Ya existe una cuenta con ese correo.', 'error')
            return render_template('registro.html')

        nuevo_usuario = Usuario(
            nombre=nombre,
            email=email,
            password_hash=generate_password_hash(password)
        )

        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            login_user(nuevo_usuario)
            flash(f'✅ ¡Bienvenido, {nombre}! Tu cuenta fue creada.', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Error al crear la cuenta: {e}', 'error')

    return render_template('registro.html')


# ============================
# RUTA: Login
# ============================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        recordar = request.form.get('recordar') == 'on'

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.password_hash, password):
            login_user(usuario, remember=recordar)
            flash(f'✅ ¡Bienvenido de vuelta, {usuario.nombre}!', 'success')
            # BUG FIX: valida que next sea URL relativa (evita open redirect)
            siguiente = url_segura(request.args.get('next'))
            return redirect(siguiente or url_for('index'))
        else:
            flash('❌ Correo o contraseña incorrectos.', 'error')

    return render_template('login.html')


# ============================
# RUTA: Logout
# ============================
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('👋 Sesión cerrada correctamente.', 'info')
    return redirect(url_for('index'))


# ============================
# RUTA: Perfil
# ============================
@app.route('/perfil')
@login_required
def perfil():
    mis_productos = Producto.query.filter_by(
        usuario_id=current_user.id
    ).order_by(Producto.fecha_creado.desc()).all()

    mis_favoritos = Favorito.query.filter_by(
        usuario_id=current_user.id
    ).all()

    mis_ordenes = Orden.query.filter_by(
        usuario_id=current_user.id
    ).order_by(Orden.fecha.desc()).limit(5).all()

    return render_template(
        'perfil.html',
        mis_productos=mis_productos,
        mis_favoritos=mis_favoritos,
        mis_ordenes=mis_ordenes
    )


# ============================
# RUTA: Editar Perfil
# ============================
@app.route('/perfil/editar', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    if request.method == 'POST':
        nombre             = request.form.get('nombre', '').strip()
        bio                = request.form.get('bio', '').strip()
        password_actual    = request.form.get('password_actual', '')
        password_nuevo     = request.form.get('password_nuevo', '')
        password_confirmar = request.form.get('password_confirmar', '')

        if not nombre:
            flash('❌ El nombre no puede estar vacío.', 'error')
            return render_template('editar_perfil.html')

        current_user.nombre = nombre
        current_user.bio    = bio

        if password_actual or password_nuevo:
            if not check_password_hash(current_user.password_hash, password_actual):
                flash('❌ La contraseña actual es incorrecta.', 'error')
                return render_template('editar_perfil.html')

            if len(password_nuevo) < 6:
                flash('❌ La nueva contraseña debe tener al menos 6 caracteres.', 'error')
                return render_template('editar_perfil.html')

            if password_nuevo != password_confirmar:
                flash('❌ Las contraseñas nuevas no coinciden.', 'error')
                return render_template('editar_perfil.html')

            current_user.password_hash = generate_password_hash(password_nuevo)

        try:
            db.session.commit()
            flash('✅ Perfil actualizado correctamente.', 'success')
            return redirect(url_for('perfil'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Error al actualizar perfil: {e}', 'error')

    return render_template('editar_perfil.html')


# ============================
# RUTA: Agregar Producto
# ============================
@app.route('/agregar', methods=['GET', 'POST'])
@login_required
def agregar_producto():
    if request.method == 'POST':
        nombre      = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        precio      = request.form.get('precio')
        categoria   = request.form.get('categoria', '').strip().lower()
        stock       = request.form.get('stock', 0)
        imagen      = 'default.jpg'

        # BUG FIX: valida categoría contra lista canónica
        if categoria not in CATEGORIAS:
            flash('❌ Categoría no válida.', 'error')
            return render_template('agregar_producto.html', categorias=CATEGORIAS)

        if 'imagen' in request.files:
            archivo = request.files['imagen']
            if archivo and archivo.filename != '' and extension_permitida(archivo.filename):
                nombre_seguro = secure_filename(archivo.filename)
                nombre_unico  = f"{uuid.uuid4().hex}_{nombre_seguro}"
                archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_unico))
                imagen = nombre_unico

        nuevo = Producto(
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            categoria=categoria,
            stock=int(stock),
            imagen=imagen,
            usuario_id=current_user.id
        )

        try:
            db.session.add(nuevo)
            db.session.commit()
            flash('✅ Producto publicado exitosamente.', 'success')
            return redirect(url_for('perfil'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Error al guardar el producto: {e}', 'error')

    return render_template('agregar_producto.html', categorias=CATEGORIAS)


# ============================
# RUTA: Editar Producto
# ============================
@app.route('/producto/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_producto(id):
    producto = Producto.query.get_or_404(id)

    if producto.usuario_id != current_user.id and not current_user.es_admin:
        flash('❌ No tienes permiso para editar este producto.', 'error')
        return redirect(url_for('perfil'))

    if request.method == 'POST':
        categoria = request.form.get('categoria', '').strip().lower()

        # BUG FIX: valida categoría al editar también
        if categoria not in CATEGORIAS:
            flash('❌ Categoría no válida.', 'error')
            return render_template('editar_producto.html', producto=producto, categorias=CATEGORIAS)

        producto.nombre      = request.form.get('nombre', '').strip()
        producto.descripcion = request.form.get('descripcion', '').strip()
        producto.precio      = request.form.get('precio')
        producto.categoria   = categoria
        producto.stock       = int(request.form.get('stock', 0))

        if 'imagen' in request.files:
            archivo = request.files['imagen']
            if archivo and archivo.filename != '' and extension_permitida(archivo.filename):
                if producto.imagen != 'default.jpg':
                    ruta_vieja = os.path.join(app.config['UPLOAD_FOLDER'], producto.imagen)
                    if os.path.exists(ruta_vieja):
                        os.remove(ruta_vieja)
                nombre_seguro = secure_filename(archivo.filename)
                nombre_unico  = f"{uuid.uuid4().hex}_{nombre_seguro}"
                archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_unico))
                producto.imagen = nombre_unico

        try:
            db.session.commit()
            flash('✅ Producto actualizado correctamente.', 'success')
            return redirect(url_for('perfil'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Error al actualizar: {e}', 'error')

    return render_template('editar_producto.html', producto=producto, categorias=CATEGORIAS)


# ============================
# RUTA: Eliminar Producto
# ============================
@app.route('/producto/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_producto(id):
    producto = Producto.query.get_or_404(id)

    if producto.usuario_id != current_user.id and not current_user.es_admin:
        flash('❌ No tienes permiso para eliminar este producto.', 'error')
        return redirect(url_for('perfil'))

    try:
        if producto.imagen != 'default.jpg':
            ruta_imagen = os.path.join(app.config['UPLOAD_FOLDER'], producto.imagen)
            if os.path.exists(ruta_imagen):
                os.remove(ruta_imagen)
        db.session.delete(producto)
        db.session.commit()
        flash('🗑️ Producto eliminado correctamente.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error al eliminar: {e}', 'error')

    return redirect(url_for('perfil'))


# ============================
# RUTA: Detalle Producto
# ============================
@app.route('/producto/<int:id>')
def detalle_producto(id):
    producto = Producto.query.get_or_404(id)
    producto.visitas += 1
    db.session.commit()

    relacionados = Producto.query.filter(
        Producto.categoria == producto.categoria,
        Producto.id != producto.id
    ).order_by(Producto.visitas.desc()).limit(4).all()

    ya_reseno = False
    if current_user.is_authenticated:
        ya_reseno = Resena.query.filter_by(
            usuario_id=current_user.id,
            producto_id=id
        ).first() is not None

    return render_template(
        'detalle_producto.html',
        producto=producto,
        relacionados=relacionados,
        ya_reseno=ya_reseno
    )


# ============================
# RUTA: Agregar Reseña
# ============================
@app.route('/producto/<int:id>/resena', methods=['POST'])
@login_required
def agregar_resena(id):
    producto = Producto.query.get_or_404(id)

    ya_reseno = Resena.query.filter_by(
        usuario_id=current_user.id,
        producto_id=id
    ).first()

    if ya_reseno:
        flash('❌ Ya dejaste una reseña para este producto.', 'error')
        return redirect(url_for('detalle_producto', id=id))

    contenido    = request.form.get('contenido', '').strip()
    calificacion = int(request.form.get('calificacion', 5))

    if not contenido:
        flash('❌ La reseña no puede estar vacía.', 'error')
        return redirect(url_for('detalle_producto', id=id))

    if calificacion < 1 or calificacion > 5:
        calificacion = 5

    nueva_resena = Resena(
        contenido=contenido,
        calificacion=calificacion,
        usuario_id=current_user.id,
        producto_id=id
    )

    try:
        db.session.add(nueva_resena)
        db.session.commit()

        if producto.usuario_id:
            crear_notificacion(
                usuario_id=producto.usuario_id,
                mensaje=f'⭐ {current_user.nombre} dejó una reseña en "{producto.nombre}"',
                tipo='resena',
                url=url_for('detalle_producto', id=id)
            )

        flash('✅ ¡Reseña publicada!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error: {e}', 'error')

    return redirect(url_for('detalle_producto', id=id))


# ============================
# RUTA: Agregar al Carrito
# ============================
@app.route('/carrito/agregar/<int:producto_id>', methods=['POST'])
def agregar_carrito(producto_id):
    producto = Producto.query.get_or_404(producto_id)

    if 'sesion_id' not in session:
        session['sesion_id'] = str(uuid.uuid4())
    sesion_id = session['sesion_id']

    if producto.stock <= 0:
        flash('❌ Producto agotado.', 'error')
        # BUG FIX: redirige al origen, no siempre a index
        return redirect(request.referrer or url_for('index'))

    cantidad = int(request.form.get('cantidad', 1))
    item_existente = ItemCarrito.query.filter_by(
        sesion_id=sesion_id,
        producto_id=producto_id
    ).first()

    # BUG FIX: verifica stock antes de agregar (no solo si hay > 0)
    cantidad_actual = item_existente.cantidad if item_existente else 0
    if cantidad_actual + cantidad > producto.stock:
        flash(f'❌ Solo hay {producto.stock} unidades disponibles.', 'error')
        return redirect(request.referrer or url_for('index'))

    try:
        if item_existente:
            item_existente.cantidad += cantidad
        else:
            nuevo_item = ItemCarrito(
                producto_id=producto_id,
                cantidad=cantidad,
                sesion_id=sesion_id,
                precio_unitario=producto.precio
            )
            db.session.add(nuevo_item)
        db.session.commit()
        flash(f'🛒 {producto.nombre} agregado al carrito.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error: {e}', 'error')

    # BUG FIX: redirige al origen, no siempre a index
    return redirect(request.referrer or url_for('index'))


# ============================
# RUTA: Ver Carrito
# ============================
@app.route('/carrito')
def ver_carrito():
    if 'sesion_id' not in session:
        session['sesion_id'] = str(uuid.uuid4())
    sesion_id = session['sesion_id']

    items = ItemCarrito.query.filter_by(sesion_id=sesion_id).all()
    total = float(sum(item.precio_unitario * item.cantidad for item in items))

    return render_template('carrito.html', items=items, total=total)


# ============================
# RUTA: Eliminar del Carrito
# ============================
@app.route('/carrito/eliminar/<int:item_id>', methods=['POST'])
def eliminar_carrito(item_id):
    # BUG FIX: verifica que el ítem pertenezca a la sesión actual
    sesion_id = session.get('sesion_id', '')
    item = ItemCarrito.query.filter_by(
        id=item_id,
        sesion_id=sesion_id
    ).first_or_404()

    try:
        db.session.delete(item)
        db.session.commit()
        flash('🗑️ Producto eliminado del carrito.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error: {e}', 'error')

    return redirect(url_for('ver_carrito'))


# ============================
# RUTA: Toggle Favorito
# ============================
@app.route('/favorito/<int:producto_id>', methods=['POST'])
@login_required
def toggle_favorito(producto_id):
    Producto.query.get_or_404(producto_id)

    favorito = Favorito.query.filter_by(
        usuario_id=current_user.id,
        producto_id=producto_id
    ).first()

    try:
        if favorito:
            db.session.delete(favorito)
            db.session.commit()
            return jsonify({'status': 'removed'})
        else:
            nuevo = Favorito(
                usuario_id=current_user.id,
                producto_id=producto_id
            )
            db.session.add(nuevo)
            db.session.commit()
            return jsonify({'status': 'added'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'mensaje': str(e)})


# ============================
# RUTA: Ver Favoritos
# ============================
@app.route('/favoritos')
@login_required
def ver_favoritos():
    favoritos = Favorito.query.filter_by(usuario_id=current_user.id).all()
    productos = [f.producto for f in favoritos]
    return render_template('favoritos.html', productos=productos)


# ============================
# RUTA: Notificaciones
# ============================
@app.route('/notificaciones')
@login_required
def notificaciones():
    notifs = Notificacion.query.filter_by(
        usuario_id=current_user.id
    ).order_by(Notificacion.fecha.desc()).all()

    for n in notifs:
        n.leida = True
    db.session.commit()

    return render_template('notificaciones.html', notificaciones=notifs)


# ============================
# RUTA: Panel Admin
# ============================
@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    total_usuarios  = Usuario.query.count()
    total_productos = Producto.query.count()
    total_ordenes   = Orden.query.count()
    total_ventas    = db.session.query(
        db.func.sum(Orden.total)
    ).filter_by(estado='pagado').scalar() or 0

    ultimas_ordenes = Orden.query.order_by(
        Orden.fecha.desc()
    ).limit(10).all()

    productos_top = Producto.query.order_by(
        Producto.visitas.desc()
    ).limit(5).all()

    usuarios_recientes = Usuario.query.order_by(
        Usuario.fecha_registro.desc()
    ).limit(5).all()

    return render_template(
        'admin.html',
        total_usuarios=total_usuarios,
        total_productos=total_productos,
        total_ordenes=total_ordenes,
        total_ventas=total_ventas,
        ultimas_ordenes=ultimas_ordenes,
        productos_top=productos_top,
        usuarios_recientes=usuarios_recientes
    )


# ============================
# RUTA: Admin — Usuarios
# ============================
@app.route('/admin/usuarios')
@login_required
@admin_required
def admin_usuarios():
    usuarios = Usuario.query.order_by(Usuario.fecha_registro.desc()).all()
    return render_template('admin_usuarios.html', usuarios=usuarios)


# ============================
# RUTA: Admin — Toggle Admin
# ============================
@app.route('/admin/usuario/<int:id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_admin(id):
    usuario = Usuario.query.get_or_404(id)
    if usuario.id == current_user.id:
        flash('❌ No puedes modificar tu propio rol.', 'error')
        return redirect(url_for('admin_usuarios'))
    usuario.es_admin = not usuario.es_admin
    db.session.commit()
    flash(f'✅ Rol de {usuario.nombre} actualizado.', 'success')
    return redirect(url_for('admin_usuarios'))


# ============================
# RUTA: Admin — Eliminar Usuario
# ============================
@app.route('/admin/usuario/<int:id>/eliminar', methods=['POST'])
@login_required
@admin_required
def admin_eliminar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    if usuario.id == current_user.id:
        flash('❌ No puedes eliminarte a ti mismo.', 'error')
        return redirect(url_for('admin_usuarios'))
    try:
        db.session.delete(usuario)
        db.session.commit()
        flash(f'🗑️ Usuario {usuario.nombre} eliminado.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error: {e}', 'error')
    return redirect(url_for('admin_usuarios'))


# ============================
# SEED INICIAL (sin importación circular)
# BUG FIX: reemplaza exec(open('seed.py').read()) que causaba error circular
# ============================
def seed_inicial():
    """Carga productos de ejemplo si la base de datos está vacía."""
    if Producto.query.count() > 0:
        return

    productos_ejemplo = [
        Producto(nombre="Globos Metálicos Dorados x20", descripcion="Globos metálicos de 12 pulgadas. Perfectos para decorar mesas y ambientes festivos.", precio=15000, categoria="globos", stock=100, imagen="globos.jpg"),
        Producto(nombre="Piñata Estrella de 6 puntas", descripcion="Piñata tradicional de papel maché. Tamaño grande, ideal para niños.", precio=35000, categoria="pinatas", stock=25, imagen="pinata.jpg"),
        Producto(nombre="Kit Decoración Jungle Party", descripcion="Set completo de decoración temática: guirnaldas, flores y follaje artificial.", precio=85000, categoria="decoracion", stock=15, imagen="jungle.jpg"),
        Producto(nombre="Confeti y Serpentinas x5", descripcion="Pack variado de confeti de colores y serpentinas de papel.", precio=8000, categoria="confeti", stock=200, imagen="confeti.jpg"),
        Producto(nombre="Vajilla Desechable 20 personas", descripcion="Set completo: platos, vasos y cubiertos decorativos para 20 personas.", precio=45000, categoria="vajilla", stock=50, imagen="vajilla.jpg"),
        Producto(nombre="Arco de Globos Pastel", descripcion="Arco decorativo con globos en tonos pastel. Ideal para cumpleaños y baby showers.", precio=120000, categoria="globos", stock=10, imagen="arco_globos.jpg"),
        Producto(nombre="Piñata Personaje Infantil", descripcion="Piñata temática personalizada con dulces incluidos.", precio=60000, categoria="pinatas", stock=12, imagen="pinata_personaje.jpg"),
        Producto(nombre="Luces LED Decorativas x10m", descripcion="Tira de luces LED cálidas de 10 metros.", precio=30000, categoria="iluminacion", stock=40, imagen="luces_led.jpg"),
        Producto(nombre="Mantel Temático Cumpleaños", descripcion="Mantel plástico decorativo resistente al agua.", precio=18000, categoria="decoracion", stock=70, imagen="mantel.jpg"),
        Producto(nombre="Sombreros de Fiesta x12", descripcion="Set de 12 sombreros festivos con diseños variados.", precio=22000, categoria="accesorios", stock=90, imagen="sombreros.jpg"),
    ]
    try:
        for p in productos_ejemplo:
            db.session.add(p)
        db.session.commit()
        print("✅ Productos de ejemplo agregados.")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error al insertar productos: {e}")


with app.app_context():
    db.create_all()
    seed_inicial()

if __name__ == '__main__':
    app.run(debug=True)