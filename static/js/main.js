// main.js — Interactividad y animaciones del marketplace

document.addEventListener('DOMContentLoaded', function () {
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';

    // CSRF global: agrega token a formularios POST y peticiones fetch mutables.
    if (csrfToken) {
        document.querySelectorAll('form[method="POST"], form[method="post"]').forEach(function (form) {
            if (!form.querySelector('input[name="csrf_token"]')) {
                const hidden = document.createElement('input');
                hidden.type = 'hidden';
                hidden.name = 'csrf_token';
                hidden.value = csrfToken;
                form.appendChild(hidden);
            }
        });

        if (window.fetch && !window.__csrfFetchPatched) {
            const originalFetch = window.fetch.bind(window);
            window.fetch = function (resource, options = {}) {
                const method = (options.method || 'GET').toUpperCase();
                const needsToken = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);

                if (needsToken) {
                    const headers = new Headers(options.headers || {});
                    if (!headers.has('X-CSRFToken')) {
                        headers.set('X-CSRFToken', csrfToken);
                    }
                    options.headers = headers;
                }

                return originalFetch(resource, options);
            };
            window.__csrfFetchPatched = true;
        }
    }

    // ============================
    // VISTA PREVIA DE IMAGEN AL SUBIR
    // ============================
    const inputImagen = document.getElementById('imagen');
    const previewContenedor = document.getElementById('preview-imagen');
    const MAX_SIZE = 2 * 1024 * 1024; // 2MB

    if (inputImagen && previewContenedor) {
        inputImagen.addEventListener('change', function () {
            const archivo = this.files[0];

            // ✅ FIX 4: Validación de tamaño antes de mostrar preview
            if (archivo.size > MAX_SIZE) {
                alert('❌ La imagen no puede superar 2MB.');
                inputImagen.value = '';
                previewContenedor.innerHTML = '';
                return;
            }

            if (archivo && archivo.type.startsWith('image/')) {
                const lector = new FileReader();

                lector.onload = function (e) {
                    previewContenedor.innerHTML = `
                        <img src="${e.target.result}"
                             alt="Vista previa"
                             style="max-height:200px; border-radius:10px; margin-top:0.5rem;">
                    `;
                };

                lector.readAsDataURL(archivo);
            }
        });
    }

    // ============================
    // AUTO-OCULTAR MENSAJES FLASH
    // ✅ FIX 3: dentro de DOMContentLoaded
    // ============================
    setTimeout(function () {
        document.querySelectorAll('.flash').forEach(function (flash) {
            flash.style.transition = 'opacity 0.5s ease';
            flash.style.opacity = '0';
            setTimeout(() => flash.remove(), 500);
        });
    }, 4000);

    // ============================
    // ANIMACIÓN DE ENTRADA PARA TARJETAS
    // ============================
    const tarjetas = document.querySelectorAll('.producto-card');

    // ✅ FIX 1: ya no inyectamos CSS desde JS — los estilos van en style.css
    if (tarjetas.length > 0) {
        const observador = new IntersectionObserver(function (entradas) {
            entradas.forEach(function (entrada) {
                if (entrada.isIntersecting) {
                    entrada.target.classList.add('visible');
                    // Dejamos de observar la tarjeta una vez animada
                    observador.unobserve(entrada.target);
                }
            });
        }, { threshold: 0.1 });

        tarjetas.forEach(tarjeta => observador.observe(tarjeta));
    }

});
