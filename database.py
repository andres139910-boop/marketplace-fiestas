# -*- coding: utf-8 -*-
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()


class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id             = db.Column(db.Integer, primary_key=True)
    nombre         = db.Column(db.String(100), nullable=False)
    email          = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash  = db.Column(db.String(256), nullable=False)
    es_vendedor    = db.Column(db.Boolean, default=True)
    es_admin       = db.Column(db.Boolean, default=False)
    google_id      = db.Column(db.String(100), unique=True, nullable=True)
    avatar         = db.Column(db.String(200), nullable=True)
    bio            = db.Column(db.Text, nullable=True)
    fecha_registro = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    productos      = db.relationship('Producto', backref='vendedor', lazy=True)
    favoritos      = db.relationship('Favorito', backref='usuario', lazy=True)
    resenas        = db.relationship('Resena', backref='autor', lazy=True)
    notificaciones = db.relationship('Notificacion', backref='usuario', lazy=True)

    def __repr__(self):
        return f'<Usuario {self.email}>'


class Producto(db.Model):
    __tablename__ = 'productos'

    id           = db.Column(db.Integer, primary_key=True)
    nombre       = db.Column(db.String(100), nullable=False)
    descripcion  = db.Column(db.Text, nullable=False)
    precio       = db.Column(db.Numeric(10, 2), nullable=False)
    imagen       = db.Column(db.String(200), default='default.jpg')
    categoria    = db.Column(db.String(50), nullable=False, index=True)
    stock        = db.Column(db.Integer, default=0)
    visitas      = db.Column(db.Integer, default=0)
    fecha_creado = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    usuario_id   = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

    favoritos = db.relationship('Favorito', backref='producto', lazy=True)
    resenas   = db.relationship('Resena', backref='producto', lazy=True)

    def promedio_resenas(self):
        if not self.resenas:
            return 0
        return round(sum(r.calificacion for r in self.resenas) / len(self.resenas), 1)

    def __repr__(self):
        return f'<Producto {self.nombre}>'

    def to_dict(self):
        return {
            'id':          self.id,
            'nombre':      self.nombre,
            'descripcion': self.descripcion,
            'precio':      float(self.precio),
            'imagen':      self.imagen,
            'categoria':   self.categoria,
            'stock':       self.stock,
            'visitas':     self.visitas
        }


class ItemCarrito(db.Model):
    __tablename__ = 'carrito'

    id              = db.Column(db.Integer, primary_key=True)
    producto_id     = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad        = db.Column(db.Integer, default=1)
    sesion_id       = db.Column(db.String(100), nullable=False, index=True)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    fecha_agregado  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    producto = db.relationship(
        'Producto',
        backref=db.backref('items_carrito', cascade='all, delete-orphan')
    )


class Favorito(db.Model):
    __tablename__ = 'favoritos'

    id          = db.Column(db.Integer, primary_key=True)
    usuario_id  = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    fecha       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Resena(db.Model):
    __tablename__ = 'resenas'

    id           = db.Column(db.Integer, primary_key=True)
    contenido    = db.Column(db.Text, nullable=False)
    calificacion = db.Column(db.Integer, nullable=False)
    usuario_id   = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    producto_id  = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    fecha        = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Resena producto={self.producto_id} calif={self.calificacion}>'


class Orden(db.Model):
    __tablename__ = 'ordenes'

    id            = db.Column(db.Integer, primary_key=True)
    usuario_id    = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    sesion_id     = db.Column(db.String(100), nullable=False)
    total         = db.Column(db.Numeric(10, 2), nullable=False)
    estado        = db.Column(db.String(30), default='pendiente')
    mp_preference = db.Column(db.String(200), nullable=True)
    mp_payment_id = db.Column(db.String(200), nullable=True)
    fecha         = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    items = db.relationship('ItemOrden', backref='orden', lazy=True)

    def __repr__(self):
        return f'<Orden {self.id} estado={self.estado}>'


class ItemOrden(db.Model):
    __tablename__ = 'items_orden'

    id              = db.Column(db.Integer, primary_key=True)
    orden_id        = db.Column(db.Integer, db.ForeignKey('ordenes.id'), nullable=False)
    producto_id     = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad        = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)

    producto = db.relationship('Producto')


class Notificacion(db.Model):
    __tablename__ = 'notificaciones'

    id         = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    mensaje    = db.Column(db.Text, nullable=False)
    leida      = db.Column(db.Boolean, default=False)
    tipo       = db.Column(db.String(30), default='info')
    url        = db.Column(db.String(200), nullable=True)
    fecha      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Notificacion usuario={self.usuario_id} leida={self.leida}>'
