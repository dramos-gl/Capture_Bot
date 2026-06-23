# Guía de Adaptación de Estructura UI basada en Atomic Design

Esta guía describe cómo exportar, adaptar y estructurar la metodología de **Atomic Design** utilizada en este proyecto para implementarla en cualquier otro desarrollo de software (sea PySide, Flet, React, Vue, etc.).

---

## 1. Estructura de Directorios Propuesta

Para mantener una separación clara entre la lógica de negocio y los componentes puramente visuales de la interfaz de usuario, se recomienda la siguiente estructura:

```text
mi_nuevo_proyecto/
│
└─── src/
     └─── ui/
          ├─── views/             # Vistas/Páginas específicas del negocio (no reutilizables)
          └─── design_system/     # Sistema de diseño reutilizable y agnóstico
               ├─── tokens/       # Constantes: colores, tamaños, fuentes, espaciados
               ├─── themes/       # Definiciones de temas (Claro / Oscuro)
               ├─── layout/       # Componentes de estructura global (Sidebars, Rejillas)
               ├─── utils/        # Helpers y utilidades visuales
               ├─── theme_manager.py # Administrador global del estado del tema
               └─── components/   # Componentes clasificados con Atomic Design
                    ├─── __init__.py  # Exportador/Punto de entrada de componentes
                    ├─── atoms/       # Componentes básicos indivisibles
                    ├─── molecules/   # Mezclas de átomos con propósito UI específico
                    └─── organisms/   # Bloques complejos y funcionales
```

---

## 2. Clasificación y Reglas de los Componentes

Para asegurar la escalabilidad del sistema de diseño, clasifica rigurosamente cada componente:

| Categoría | Descripción | Regla Clave | Ejemplos |
| :--- | :--- | :--- | :--- |
| **Átomos (`atoms`)** | Bloques de construcción básicos e indivisibles de la UI. | No deben importar ni depender de ningún otro componente del sistema de diseño. | Botones simples, etiquetas (`labels`), indicadores de carga (`skeletons`), iconos. |
| **Moléculas (`molecules`)** | Agrupaciones de dos o más átomos que funcionan juntos como una unidad funcional simple. | Tienen un propósito de interfaz de usuario específico pero siguen siendo genéricos (sin lógica de negocio). | Buscadores (input + icono), inputs etiquetados (label + input + mensaje error), tarjetas básicas (`cards`). |
| **Organismos (`organisms`)** | Estructuras de interfaz complejas compuestas por moléculas y/o átomos. | Pueden interactuar con el estado global de la interfaz, pero no deben acoplarse rígidamente a APIs específicas. | Barras de navegación completas, formularios dinámicos estructurados, paneles de filtros avanzados. |

---

## 3. Implementación del Punto de Entrada Centralizado

Para evitar importaciones redundantes y extensas desde la aplicación, utiliza un archivo de exportación global (`__init__.py` en Python, o `index.ts/js` en frontend) en la raíz de `components/`.

### Ejemplo en Python (`components/__init__.py`)
```python
# Exposición limpia de átomos
from .atoms.gl_button import CustomButton
from .atoms.gl_skeleton import CustomSkeleton

# Exposición limpia de moléculas
from .molecules.gl_card import CustomCard
from .molecules.gl_input import CustomInputField

# Exposición limpia de organismos
from .organisms.gl_filter_panel import FilterPanel
```

Esto simplifica el desarrollo de las vistas de negocio considerablemente:
```python
# Uso limpio en cualquier vista
from src.ui.design_system.components import CustomButton, CustomCard
```

---

## 4. Buenas Prácticas para la Adaptación

> [!IMPORTANT]
> **Agnosticismo de Datos**
> Los componentes dentro de `design_system` nunca deben conocer tus repositorios, bases de datos o servicios de negocio. Si un componente necesita datos, pásaselos como parámetros/propiedades. Si necesita responder a una acción, expón un callback o una señal.

> [!TIP]
> **Uso de Tokens de Diseño**
> Evita los valores quemados (*hardcoded*) como colores `#1a202c` o tamaños `12px` directamente en los componentes. Centraliza estos valores en `tokens/` y haz que los componentes consuman estas constantes. Esto te permitirá cambiar toda la identidad visual del nuevo proyecto modificando un solo archivo.

> [!NOTE]
> **Despliegue del Administrador de Temas**
> Implementa un `theme_manager.py` centralizado en tu sistema de diseño. Este administrador debe encargarse de propagar y actualizar dinámicamente las hojas de estilo o propiedades en tiempo de ejecución para todos los componentes activos en la aplicación.
