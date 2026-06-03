import queue
import os
import json
import logging
import shutil
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Configuración básica de customtkinter para el tema claro premium de alta fidelidad
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

logger = logging.getLogger("OptimaCaptureBot.GUI")

# Importar gestión de configuración
from app import settings
from app.excel_handler import cargar_catalog_rfc
from app.validator import es_rfc_permitido
from app.paths import SCREENSHOTS_DIR


class OptimaCaptureApp(ctk.CTk):
    def __init__(self, excel_path, event_queue, orchestrator):
        super().__init__()
        
        self.excel_path = excel_path
        self.event_queue = event_queue
        self.orchestrator = orchestrator
        # Cargar rutas guardadas
        self.excel_path = settings.get_excel_path() or self.excel_path
        
        # Guardar estados de error actuales para el panel interactivo
        self.ultimo_registro_fallido = None
        self.ultima_captura_error = None
        self.fila_error_actual = None
        
        # Configuración de Ventana (Fiel a la geometría original y la proporción de la captura)
        self.title("Optima Capture Bot — MVP v1.1")
        self.geometry("1100x780")
        self.minsize(1050, 720)
        self.configure(fg_color="#F1F5F9")  # Fondo general gris azulado muy limpio y moderno
        
        # --- CONFIGURACIÓN DE ICONO (COMPATIBLE CON PYINSTALLER) ---
        self._establecer_icono()
        
        # Diseño responsivo en cuadrícula
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # La consola de logs se expande de forma prioritaria
        
        # Construir Interfaz Gráfica
        self._crear_cabecera()
        self._crear_paneles_superiores()
        self._crear_consola_logs()
        self._crear_panel_errores()
        self._crear_barra_estado()
        
        # Validar rutas después de que los botones existen
        self._validar_rutas()
        
        # Iniciar ciclo de lectura de la cola de eventos (Thread-Safe)
        self.after(100, self.procesar_cola)
        
        # Interceptar el cierre de la ventana
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """Maneja el evento de cierre de ventana para limpiar procesos en segundo plano."""
        if self.orchestrator:
            self._agregar_log_consola("Deteniendo procesos en segundo plano. Espere...", "WARNING")
            self.orchestrator.detener()
            
            # Si el scraper sigue abierto, forzar cierre para evitar procesos zombies
            if self.orchestrator.scraper:
                self.orchestrator.scraper.cerrar()
                
        self.destroy()

    def _crear_cabecera(self):
        """
        Cabecera premium azul oscuro idéntica a la imagen, con botones de configuración y alternancia de tema.
        """
        # Color azul marino profundo premium (#1B365D o #2C4E80)
        self.header_frame = ctk.CTkFrame(self, fg_color="#1E3E62", height=60, corner_radius=8)
        self.header_frame.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        # Icono y Título
        title_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_container.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        self.title_label = ctk.CTkLabel(
            title_container, 
            text="🚀  OPTIMA CAPTURE BOT — MVP v1.1", 
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#FFFFFF"
        )
        self.title_label.pack(side="left")
        
        # Contenedor de controles a la derecha (Badge de estado + Botones circulares)
        controls_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        controls_container.grid(row=0, column=2, padx=15, pady=10, sticky="e")
        
        # Badge de Estado del Portal
        self.status_satq_label = ctk.CTkLabel(
            controls_container,
            text="Portal: INACTIVO",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#FFFFFF",
            fg_color="#4B6584",  # Gris azulado de contraste
            corner_radius=15,
            padx=15,
            pady=4,
            height=28
        )
        self.status_satq_label.pack(side="left", padx=(0, 10))
        
        # Botón Circular 1: Configuración
        self.btn_icon_config = ctk.CTkButton(
            controls_container, text="⚙️", font=ctk.CTkFont(size=14),
            fg_color="transparent", hover_color="#2D5A88", text_color="#FFFFFF",
            width=28, height=28, corner_radius=14, command=self.action_change_url
        )
        self.btn_icon_config.pack(side="left", padx=2)
        
         # Botón Circular 2: Usuario / Perfil
        self.btn_icon_user = ctk.CTkButton(
            controls_container, text="👤", font=ctk.CTkFont(size=14),
            fg_color="transparent", hover_color="#2D5A88", text_color="#FFFFFF",
            width=28, height=28, corner_radius=14
        )
        self.btn_icon_user.pack(side="left", padx=2)


    def _crear_paneles_superiores(self):
        """
        Paneles superiores con el espectacular diseño e iconos idénticos a la imagen.
        """
        self.upper_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.upper_frame.grid(row=1, column=0, padx=15, pady=5, sticky="nsew")
        self.upper_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="equal")
        
        # -------------------------------------------------------------
        # 1. PANEL DE CONTROLES OPERATIVOS (Columna 0)
        # -------------------------------------------------------------
        self.control_frame = ctk.CTkFrame(self.upper_frame, fg_color="#FFFFFF", corner_radius=8, border_color="#E2E8F0", border_width=1)
        self.control_frame.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="nsew")
        
        lbl_ctrl = ctk.CTkLabel(
            self.control_frame, text="⚙️  CONTROLES OPERATIVOS", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#1E293B"
        )
        lbl_ctrl.pack(anchor="w", padx=15, pady=(15, 12))
        
        # Switch Omitir Ya Generadas
        self.switch_omitir_generadas = ctk.CTkSwitch(
            self.control_frame, text="Omitir 'Ya Generadas'",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#1E293B",
            onvalue=True, offvalue=False
        )
        self.switch_omitir_generadas.select()  # Activado por defecto
        self.switch_omitir_generadas.pack(anchor="w", padx=15, pady=(0, 10))

        # Switch Modo Autónomo (con persistencia en settings.json)
        self.switch_modo_autonomo = ctk.CTkSwitch(
            self.control_frame, text="🤖 Modo Autónomo (Sin confirmación)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#1E293B",
            onvalue=True, offvalue=False,
            command=self.action_toggle_modo_autonomo
        )
        # Cargar estado guardado
        if settings.get_modo_timbrado() == "autonomo":
            self.switch_modo_autonomo.select()
        else:
            self.switch_modo_autonomo.deselect()
        self.switch_modo_autonomo.pack(anchor="w", padx=15, pady=(0, 15))
        
        # Botón Iniciar Bot en color azul marino profundo con texto blanco
        self.btn_iniciar = ctk.CTkButton(
            self.control_frame, text="▶  Iniciar Bot", fg_color="#1E3E62", hover_color="#152B44",
            text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            border_width=0, corner_radius=6, height=32, command=self.action_iniciar
        )
        self.btn_iniciar.pack(fill="x", padx=15, pady=4)
        
        # Botones blancos con borde gris sutil y letras oscuras
        self.btn_pausar = ctk.CTkButton(
            self.control_frame, text="⏸  Pausar", fg_color="#FFFFFF", hover_color="#F8FAFC",
            text_color="#1E293B", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            border_color="#CBD5E1", border_width=1, corner_radius=6, height=32, state="disabled", command=self.action_pausar
        )
        self.btn_pausar.pack(fill="x", padx=15, pady=4)
        
        self.btn_detener = ctk.CTkButton(
            self.control_frame, text="■  Detener Seguro", fg_color="#FFFFFF", hover_color="#F8FAFC",
            text_color="#1E293B", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            border_color="#CBD5E1", border_width=1, corner_radius=6, height=32, state="disabled", command=self.action_detener
        )
        self.btn_detener.pack(fill="x", padx=15, pady=4)
        
        self.btn_select_excel = ctk.CTkButton(
            self.control_frame, text="📊  Seleccionar Excel", fg_color="#FFFFFF", hover_color="#F8FAFC",
            text_color="#1E293B", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            border_color="#CBD5E1", border_width=1, corner_radius=6, height=32, command=self.action_select_excel
        )
        self.btn_select_excel.pack(fill="x", padx=15, pady=4)

        self.btn_select_download = ctk.CTkButton(
            self.control_frame, text="📁  Carpeta Descargas", fg_color="#FFFFFF", hover_color="#F8FAFC",
            text_color="#1E293B", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            border_color="#CBD5E1", border_width=1, corner_radius=6, height=32, command=self.action_select_download
        )
        self.btn_select_download.pack(fill="x", padx=15, pady=4)

        # Botón para la nueva herramienta de validación de PDFs
        self.btn_validar_pdfs = ctk.CTkButton(
            self.control_frame, text="🔍  Validar PDFs", fg_color="#FFFFFF", hover_color="#F8FAFC",
            text_color="#1E293B", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            border_color="#CBD5E1", border_width=1, corner_radius=6, height=32, command=self.action_validar_pdfs
        )
        self.btn_validar_pdfs.pack(fill="x", padx=15, pady=4)
        
        # Botón Configurar URL con engrane integrado a la derecha
        self.btn_change_url = ctk.CTkButton(
            self.control_frame, text="🔗  Configurar URL SATQ", fg_color="#FFFFFF", hover_color="#F8FAFC",
            text_color="#1E293B", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            border_color="#CBD5E1", border_width=1, corner_radius=6, height=32, command=self.action_change_url
        )
        self.btn_change_url.pack(fill="x", padx=15, pady=(4, 15))
        
        # Panel informativo del Catálogo RFC al final de la columna (en recuadro gris sutil con icono info)
        self.catalog_box = ctk.CTkFrame(self.control_frame, fg_color="#F8FAFC", border_color="#E2E8F0", border_width=1, corner_radius=6)
        self.catalog_box.pack(fill="x", padx=15, pady=(0, 15))
        
        self.lbl_catalog_info = ctk.CTkLabel(
            self.catalog_box, 
            text="RFC: -- | Razón Social: -- |\nCP: --", 
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), 
            text_color="#64748B", 
            justify="left",
            anchor="w"
        )
        self.lbl_catalog_info.pack(side="left", padx=10, pady=8, fill="x", expand=True)
        
        self.lbl_info_icon = ctk.CTkLabel(self.catalog_box, text="ⓘ", font=ctk.CTkFont(size=14, weight="bold"), text_color="#94A3B8")
        self.lbl_info_icon.pack(side="right", padx=10)

        # -------------------------------------------------------------
        # 2. PANEL DE MÉTRICAS DEL LOTE (Columna 1)
        # -------------------------------------------------------------
        self.metrics_frame = ctk.CTkFrame(self.upper_frame, fg_color="#FFFFFF", corner_radius=8, border_color="#E2E8F0", border_width=1)
        self.metrics_frame.grid(row=0, column=1, padx=4, pady=0, sticky="nsew")
        
        lbl_metrics = ctk.CTkLabel(
            self.metrics_frame, text="📊  MÉTRICAS DEL LOTE", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#1E293B"
        )
        lbl_metrics.pack(anchor="w", padx=15, pady=(15, 8))
        
        # Grid interno principal para las métricas
        self.grid_metrics = ctk.CTkFrame(self.metrics_frame, fg_color="transparent")
        self.grid_metrics.pack(fill="both", expand=True, padx=10, pady=2)
        
        # Fila superior (3 Columnas con fondos de colores muy llamativos)
        self.row1_metrics = ctk.CTkFrame(self.grid_metrics, fg_color="transparent")
        self.row1_metrics.pack(fill="x", pady=3)
        self.row1_metrics.columnconfigure((0, 1, 2), weight=1, uniform="equal")
        
        self.card_pendientes = self._crear_tarjeta_color(self.row1_metrics, "⏰ Pendientes", "0", "#3B82F6", 0)
        self.card_exitosos = self._crear_tarjeta_color(self.row1_metrics, "✅ Exitosos", "0", "#10B981", 1)
        self.card_errores = self._crear_tarjeta_color(self.row1_metrics, "⚠️ Errores", "0", "#EF4444", 2)
        
        # Fila del medio (2 Columnas con bordes delgados)
        self.row2_metrics = ctk.CTkFrame(self.grid_metrics, fg_color="transparent")
        self.row2_metrics.pack(fill="x", pady=3)
        self.row2_metrics.columnconfigure((0, 1), weight=1, uniform="equal")
        
        self.card_total = self._crear_tarjeta_borde(self.row2_metrics, "📄 Total Registros", "0", 0)
        self.card_lote = self._crear_tarjeta_borde(self.row2_metrics, "📁 Lote Activo", "--", 1)
        
        # Fila inferior (2 Columnas con fondos gris muy claro)
        self.row3_metrics = ctk.CTkFrame(self.grid_metrics, fg_color="transparent")
        self.row3_metrics.pack(fill="x", pady=3)
        self.row3_metrics.columnconfigure((0, 1), weight=1, uniform="equal")
        
        self.card_omitidos = self._crear_tarjeta_gris(self.row3_metrics, "➤ Omitidos", "0", 0)
        self.card_revision  = self._crear_tarjeta_gris(self.row3_metrics, "🔍 Revisión", "0", 1)
        
        # Fila inferior de métricas compacta
        self.metrics_footer = ctk.CTkFrame(self.metrics_frame, fg_color="transparent")
        self.metrics_footer.pack(fill="x", padx=15, pady=(8, 12))
        
        self.lbl_update_time = ctk.CTkLabel(
            self.metrics_footer, text="Última actualización: --",
            font=ctk.CTkFont(family="Segoe UI", size=10), text_color="#64748B"
        )
        self.lbl_update_time.pack(side="left")
        
        self.btn_refresh = ctk.CTkButton(
            self.metrics_footer, text="↻", font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#FFFFFF", hover_color="#F8FAFC", text_color="#64748B",
            border_color="#CBD5E1", border_width=1, corner_radius=5, width=28, height=28,
            command=self.action_abrir_excel
        )
        self.btn_refresh.pack(side="right")

        # -------------------------------------------------------------
        # 3. PANEL DE MONITOREO EN TIEMPO REAL (Columna 2)
        # -------------------------------------------------------------
        self.monitor_frame = ctk.CTkFrame(self.upper_frame, fg_color="#FFFFFF", corner_radius=8, border_color="#E2E8F0", border_width=1)
        self.monitor_frame.grid(row=0, column=2, padx=(8, 0), pady=0, sticky="nsew")
        
        # Cabecera con título e icono WiFi/Señal a la derecha
        title_mon_frame = ctk.CTkFrame(self.monitor_frame, fg_color="transparent")
        title_mon_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        lbl_mon = ctk.CTkLabel(
            title_mon_frame, text="🛒  MONITOREO EN TIEMPO REAL", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#1E293B"
        )
        lbl_mon.pack(side="left")
        
        lbl_wifi_icon = ctk.CTkLabel(
            title_mon_frame, text="((p))", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#1E3E62"
        )
        lbl_wifi_icon.pack(side="right")
        
        # Info de monitoreo alineada de forma elegante
        self.info_container = ctk.CTkFrame(self.monitor_frame, fg_color="transparent")
        self.info_container.pack(fill="x", padx=15, pady=4)
        
        self.lbl_ref_activa = self._crear_campo_monitoreo(self.info_container, "Referencia:", "--")
        self.lbl_rfc_activo = self._crear_campo_monitoreo(self.info_container, "RFC:", "--")
        self.lbl_accion_activa = self._crear_campo_monitoreo(self.info_container, "Estado:", "--")
        
        # Barra de progreso segmentada / premium
        progress_label_frame = ctk.CTkFrame(self.monitor_frame, fg_color="transparent")
        progress_label_frame.pack(fill="x", padx=15, pady=(12, 4))
        
        lbl_progreso_txt = ctk.CTkLabel(
            progress_label_frame, text="Progreso", 
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#475569"
        )
        lbl_progreso_txt.pack(side="left")
        
        self.lbl_pct = ctk.CTkLabel(
            progress_label_frame, text="0%", 
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#1E3E62"
        )
        self.lbl_pct.pack(side="right")
        
        # Barra de progreso estilizada en azul marino premium
        self.progress_bar = ctk.CTkProgressBar(self.monitor_frame, fg_color="#F1F5F9", progress_color="#1E3E62", height=10, corner_radius=5)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=15, pady=(4, 10))
        
        # Etiqueta de detalle de proceso bajo la barra
        self.lbl_progreso_detalle = ctk.CTkLabel(
            self.monitor_frame,
            text="ESPERANDO INICIO DE PROCESAMIENTO...",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#64748B",
            anchor="w"
        )
        self.lbl_progreso_detalle.pack(fill="x", padx=15, pady=(0, 15))

    # --- MÉTODOS DE CREACIÓN DE WIDGETS DE MÉTRICAS PERSONALIZADOS ---

    def _crear_tarjeta_color(self, parent, titulo, valor_defecto, color_fondo, col):
        """Crea una tarjeta de color brillante para la fila superior de métricas."""
        card = ctk.CTkFrame(parent, fg_color=color_fondo, corner_radius=6)
        card.grid(row=0, column=col, padx=3, pady=0, sticky="nsew")
        
        lbl_title = ctk.CTkLabel(
            card, text=titulo, 
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"), text_color="#FFFFFF"
        )
        lbl_title.pack(anchor="w", padx=8, pady=(8, 2))
        
        lbl_val = ctk.CTkLabel(
            card, text=valor_defecto, 
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color="#FFFFFF"
        )
        lbl_val.pack(anchor="w", padx=8, pady=(0, 8))
        
        return lbl_val

    def _crear_tarjeta_borde(self, parent, titulo, valor_defecto, col):
        """Crea una tarjeta con borde gris y fondo blanco para la fila del medio de métricas."""
        card = ctk.CTkFrame(parent, fg_color="#FFFFFF", border_color="#E2E8F0", border_width=1, corner_radius=6)
        card.grid(row=0, column=col, padx=4, pady=0, sticky="nsew")
        
        lbl_title = ctk.CTkLabel(
            card, text=titulo, 
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color="#475569"
        )
        lbl_title.pack(anchor="w", padx=10, pady=(6, 1))
        
        lbl_val = ctk.CTkLabel(
            card, text=valor_defecto, 
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#1E293B"
        )
        lbl_val.pack(anchor="w", padx=10, pady=(0, 6))
        
        return lbl_val

    def _crear_tarjeta_gris(self, parent, titulo, valor_defecto, col):
        """Crea una tarjeta de color gris claro para la fila inferior de métricas."""
        card = ctk.CTkFrame(parent, fg_color="#F8FAFC", border_color="#E2E8F0", border_width=1, corner_radius=6)
        card.grid(row=0, column=col, padx=4, pady=0, sticky="nsew")
        
        lbl_title = ctk.CTkLabel(
            card, text=titulo, 
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color="#64748B"
        )
        lbl_title.pack(anchor="w", padx=10, pady=(6, 1))
        
        lbl_val = ctk.CTkLabel(
            card, text=valor_defecto, 
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#EF4444"
        )
        lbl_val.pack(anchor="w", padx=10, pady=(0, 6))
        
        return lbl_val

    def _crear_campo_monitoreo(self, parent, label_text, valor_defecto):
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill="x", pady=3)
        
        lbl_tag = ctk.CTkLabel(
            row_frame, text=label_text, 
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color="#64748B", width=70, anchor="w"
        )
        lbl_tag.pack(side="left")
        
        lbl_val = ctk.CTkLabel(
            row_frame, text=valor_defecto, 
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#1E293B", anchor="w"
        )
        lbl_val.pack(side="left", fill="x", expand=True)
        
        return lbl_val

    def _crear_consola_logs(self):
        """
        Consola de Logs premium con fondo negro e inserción coloreada de logs.
        """
        self.logs_frame = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=8, border_color="#E2E8F0", border_width=1)
        self.logs_frame.grid(row=2, column=0, padx=15, pady=5, sticky="nsew")
        
        console_header = ctk.CTkFrame(self.logs_frame, fg_color="transparent")
        console_header.pack(fill="x", padx=15, pady=(10, 6))
        
        lbl_log = ctk.CTkLabel(
            console_header, text="⚙️  CONSOLA DE LOGS DE ACTIVIDAD", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#1E293B"
        )
        lbl_log.pack(side="left")
        
        # Botón Limpiar Logs en azul marino premium
        self.btn_limpiar = ctk.CTkButton(
            console_header, text="🗑️  Limpiar", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color="#1E3E62", hover_color="#152B44", text_color="#FFFFFF",
            border_width=0, corner_radius=5, width=80, height=26,
            command=self.action_limpiar_logs
        )
        self.btn_limpiar.pack(side="right")
        
        # Textbox de Consola de Logs (Fondo negro)
        self.log_textbox = ctk.CTkTextbox(
            self.logs_frame, 
            fg_color="#1E1E1E",  # Negro absoluto de consola
            text_color="#FFFFFF", 
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=6,
            border_color="#2D2D2D",
            border_width=1
        )
        self.log_textbox.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Placeholder inicial
        self.log_textbox.insert("end", "\n\n\t\t📝 Los logs de actividad aparecerán aquí...\n\t\t   Inicia el bot para comenzar.")
        self.log_textbox.configure(state="disabled")

    def _crear_panel_errores(self):
        """
        Panel de resolución de errores flotante, blanco y sumamente premium al final de la ventana.
        """
        # Contenedor exterior transparente para centrar el panel flotante
        self.error_outer_container = ctk.CTkFrame(self, fg_color="transparent")
        self.error_outer_container.grid(row=3, column=0, padx=15, pady=(5, 5), sticky="ew")
        
        # Panel flotante blanco e interactivo
        self.error_frame = ctk.CTkFrame(
            self.error_outer_container, 
            fg_color="#FFFFFF", 
            border_color="#CBD5E1", 
            border_width=1, 
            corner_radius=8
        )
        self.error_frame.pack(anchor="center", fill="x", padx=100, pady=2)
        
        # Contenedor interno
        content_frame = ctk.CTkFrame(self.error_frame, fg_color="transparent")
        content_frame.pack(fill="x", padx=20, pady=10)
        
        # Icono e info de incidencia
        self.lbl_error_info = ctk.CTkLabel(
            content_frame, 
            text="⚠️  PANEL DE GESTIÓN DE INCIDENCIAS  Sin fallos registrados en la sesión actual.", 
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#475569",
            anchor="w"
        )
        self.lbl_error_info.pack(side="left", fill="x", expand=True)
        
        # Botones de Acción (estilo plano, ultra moderno)
        self.btn_ver_screenshot = ctk.CTkButton(
            content_frame, text="📷  Ver Captura", fg_color="#F1F5F9", hover_color="#E2E8F0",
            text_color="#475569", border_color="#CBD5E1", border_width=1, corner_radius=5, height=28,
            state="disabled", command=self.action_ver_screenshot
        )
        self.btn_ver_screenshot.pack(side="left", padx=3)
        
        self.btn_reintentar_registro = ctk.CTkButton(
            content_frame, text="↻  Reintentar Registro", fg_color="#F1F5F9", hover_color="#E2E8F0",
            text_color="#475569", border_color="#CBD5E1", border_width=1, corner_radius=5, height=28,
            state="disabled", command=self.action_reintentar_registro
        )
        self.btn_reintentar_registro.pack(side="left", padx=3)
        
        self.btn_omitir_registro = ctk.CTkButton(
            content_frame, text="⤨  Omitir Registro", fg_color="#F1F5F9", hover_color="#E2E8F0",
            text_color="#475569", border_color="#CBD5E1", border_width=1, corner_radius=5, height=28,
            state="disabled", command=self.action_omitir_registro
        )
        self.btn_omitir_registro.pack(side="left", padx=3)
        
        self.btn_revision_manual = ctk.CTkButton(
            content_frame, text="🪱  Revisión Manual", fg_color="#2563EB", hover_color="#1D4ED8",
            text_color="#FFFFFF", border_width=0, corner_radius=5, height=28,
            state="disabled", command=self.action_revision_manual
        )
        self.btn_revision_manual.pack(side="left", padx=3)
        
        # --- BOTONES DE VALIDACIÓN PREVIA AL TIMBRADO (ocultos por defecto) ---
        self.btn_aprobar_timbrar = ctk.CTkButton(
            content_frame,
            text="✅  Aprobar Timbrado",
            fg_color="#16A34A", hover_color="#15803D",
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            height=30, corner_radius=5,
            command=self.action_aprobar_timbrar
        )
        self.btn_aprobar_timbrar.pack_forget()  # Oculto por defecto
        
        self.btn_cancelar_timbrar = ctk.CTkButton(
            content_frame,
            text="❌  Cancelar Timbrado",
            fg_color="#EF4444", hover_color="#DC2626",
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            height=30, corner_radius=5,
            command=self.action_cancelar_timbrar
        )
        self.btn_cancelar_timbrar.pack_forget()  # Oculto por defecto
        
        # Botón de Login Asistido ("Continuar") que se muestra solo al requerir login
        self.btn_login_continuar = ctk.CTkButton(
            content_frame,
            text="Continuar Proceso",
            fg_color="#16A34A",
            hover_color="#15803D",
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=130,
            command=self.action_continuar_login
        )
        self.btn_login_continuar.pack_forget()

    def _crear_barra_estado(self):
        """
        Barra de estado inferior premium con destello e icono de LED.
        """
        self.statusbar_frame = ctk.CTkFrame(self, fg_color="transparent", height=24)
        self.statusbar_frame.grid(row=4, column=0, padx=15, pady=(5, 10), sticky="ew")
        
        self.lbl_version_info = ctk.CTkLabel(
            self.statusbar_frame,
            text="OPTIMA CAPTURE BOT   |   Versión: 1.1.0   |   DR 2026",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#94A3B8"
        )
        self.lbl_version_info.pack(side="left")
        
        # LED y mensaje de sistema listo
        self.lbl_system_led = ctk.CTkLabel(
            self.statusbar_frame,
            text="🔋  Sistema listo",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#22C55E"  # LED verde brillante
        )
        self.lbl_system_led.pack(side="right")

    # --- LÓGICA DE ACTUALIZACIÓN DE EVENTOS (Thread-Safe Queue) ---

    def procesar_cola(self):
        """
        Monitorea la cola de eventos proveniente del hilo del orquestador y refresca la UI.
        """
        try:
            while True:
                evento = self.event_queue.get_nowait()
                tipo = evento.get("type")
                
                if tipo == "log":
                    self._agregar_log_consola(evento["message"], evento.get("nivel", "INFO"))
                    
                elif tipo == "metrics":
                    self.card_pendientes.configure(text=str(evento['pendientes']))
                    self.card_exitosos.configure(text=str(evento['exitosos']))
                    self.card_errores.configure(text=str(evento['errores']))
                    self.card_omitidos.configure(text=str(evento['omitidos']))
                    self.card_revision.configure(text=str(evento.get('revision', 0)))
                    self.card_total.configure(text=str(evento['total']))
                    
                    # Calcular progreso: filas definitivamente terminadas / total
                    total = evento["total"]
                    completados = (evento['exitosos'] + evento['omitidos'] 
                                   + evento['errores'] + evento.get('revision', 0))
                    pct = int((completados / total) * 100) if total > 0 else 0
                    self.progress_bar.set(completados / total if total > 0 else 0)
                    self.lbl_pct.configure(text=f"{pct}%")
                    
                    # Guardar total en la instancia para usarlo en el monitor
                    self._total_registros = total
                    
                    # Actualizar fecha y hora del sistema
                    import datetime
                    now = datetime.datetime.now().strftime("%H:%M:%S")
                    self.lbl_update_time.configure(text=f"Última actualización: {now}")
                    
                elif tipo == "status":
                    self.lbl_ref_activa.configure(text=evento['referencia'])
                    self.lbl_rfc_activo.configure(text=evento.get('rfc', '--'))
                    self.lbl_accion_activa.configure(text=f"Fila: {evento['fila']} | {evento['accion']}")
                    
                    # Mostrar el progreso dinámico en la etiqueta del monitoreo
                    total_str = str(getattr(self, '_total_registros', '?'))
                    self.lbl_progreso_detalle.configure(
                        text=f"FILA {evento['fila']} / {total_str}  —  {evento['accion'].upper()}"
                    )
                    
                    # Identificar carpeta de lote activo
                    numero_lote = ((evento["fila"] - 2) // 100) + 1
                    self.card_lote.configure(text=f"Lote_{numero_lote}")
                    
                elif tipo == "waiting_login":
                    self.status_satq_label.configure(
                        text="Portal: ESPERANDO AUTENTICACIÓN", 
                        text_color="#FFFFFF", 
                        fg_color="#D97706"  # Amber
                    )
                    self.btn_login_continuar.pack(side="right", padx=10)
                    self._agregar_log_consola("[SISTEMA] [ESPERA] Por favor, ingrese sus datos y resuelva el captcha en el navegador visible. Cuando termine, haga clic en el botón verde 'Continuar Proceso' de la aplicación.", "WARNING")
                    
                elif tipo == "login_completado":
                    self.status_satq_label.configure(
                        text="Portal: SESIÓN ACTIVA", 
                        text_color="#FFFFFF", 
                        fg_color="#16A34A"  # Verde
                    )
                    self.btn_login_continuar.pack_forget()
                    
                elif tipo == "waiting_timbrar":
                    # El bot llenó los campos y espera aprobación del operador antes de timbrar
                    razon = evento.get("razon_social", "")
                    cp_val = evento.get("cp", "")
                    self.lbl_error_info.configure(
                        text=f"⏳  VALIDACIÓN PREVIA: Revise en Chrome los campos — Razón Social: '{razon}' | CP: '{cp_val}'",
                        text_color="#1D4ED8"
                    )
                    # Cambiar color del badge de estado
                    self.status_satq_label.configure(text="Portal: ESPERANDO VALIDACIÓN", fg_color="#2563EB")
                    
                    # Ocultar temporalmente los botones de error inactivos para liberar espacio en la UI
                    self.btn_ver_screenshot.pack_forget()
                    self.btn_reintentar_registro.pack_forget()
                    self.btn_omitir_registro.pack_forget()
                    self.btn_revision_manual.pack_forget()
                    
                    # Mostrar los botones de Aprobar y Cancelar alineados a la derecha
                    self.btn_cancelar_timbrar.pack(side="right", padx=4)
                    self.btn_aprobar_timbrar.pack(side="right", padx=4)
                    
                    self._agregar_log_consola(
                        f"[VALIDACIÓN] Revise en Chrome: Razón Social='{razon}' | CP='{cp_val}'. "
                        "Apruebe o cancele con los botones.", "WARNING"
                    )
                    
                elif tipo == "timbrar_respondido":
                    # Ocultar los botones de validación y restablecer el badge
                    self.btn_aprobar_timbrar.pack_forget()
                    self.btn_cancelar_timbrar.pack_forget()
                    
                    # Restaurar los botones de error normales
                    self.btn_ver_screenshot.pack(side="left", padx=3)
                    self.btn_reintentar_registro.pack(side="left", padx=3)
                    self.btn_omitir_registro.pack(side="left", padx=3)
                    self.btn_revision_manual.pack(side="left", padx=3)
                    
                    self.status_satq_label.configure(text="Portal: ACTIVO", fg_color="#16A34A")
                    self.lbl_error_info.configure(
                        text="⚠️  PANEL DE GESTIÓN DE INCIDENCIAS  Sin fallos registrados en la sesión actual.",
                        text_color="#475569"
                    )
                    
                elif tipo == "blocked":
                    self.bell()
                    self._crear_modal_advertencia(evento["message"])
                    
                elif tipo == "finished":
                    self._agregar_log_consola("[SISTEMA] [FIN] Proceso de orquestación finalizado.", "INFO")
                    self.action_restablecer_controles()
                    
                self.event_queue.task_done()
        except queue.Empty:
            pass
            
        # Re-agendar revisión de cola
        self.after(100, self.procesar_cola)

    def _agregar_log_consola(self, mensaje, nivel):
        """
        Agrega un registro de log a la consola visual con color estandarizado de consola de sistema.
        """
        self.log_textbox.configure(state="normal")
        
        # Limpiar el placeholder si es la primera línea que se inserta
        current_text = self.log_textbox.get("1.0", "end-1c").strip()
        if "Los logs de actividad aparecerán aquí..." in current_text:
            self.log_textbox.delete("1.0", "end")
            
        # Determinar el color del mensaje o emular un coloreado sofisticado
        self.log_textbox.insert("end", mensaje + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")
        
        # Si es un log de error, actualizar el panel de fallos para dar visibilidad
        if nivel == "ERROR":
            self.lbl_error_info.configure(
                text=f"⚠️  PANEL DE GESTIÓN DE INCIDENCIAS  Fallo detectado: {mensaje.replace('[SISTEMA]', '').strip()}",
                text_color="#DC2626"
            )
            self.btn_ver_screenshot.configure(state="normal")
            self.btn_reintentar_registro.configure(state="normal")
            self.btn_omitir_registro.configure(state="normal")
            self.btn_revision_manual.configure(state="normal")

    def action_limpiar_logs(self):
        """
        Limpia toda la consola de logs.
        """
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

    def _crear_modal_advertencia(self, mensaje):
        """
        Abre una ventana emergente modal que obliga al operador a prestar atención al bloqueo del archivo.
        """
        modal = ctk.CTkToplevel(self)
        modal.title("⚠️ Archivo Excel Bloqueado")
        modal.geometry("450x220")
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()
        modal.configure(fg_color="#FFFFFF")
        
        # Centrar respecto a la ventana principal
        x = self.winfo_x() + (self.winfo_width() // 2) - 225
        y = self.winfo_y() + (self.winfo_height() // 2) - 110
        modal.geometry(f"+{x}+{y}")
        
        lbl_titulo = ctk.CTkLabel(
            modal, text="¡ACCIÓN REQUERIDA!", 
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#EF4444"
        )
        lbl_titulo.pack(pady=(20, 10))
        
        lbl_msg = ctk.CTkLabel(
            modal, 
            text=mensaje + "\n\nEl bot continuará automáticamente en cuanto cierre el Excel.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#475569",
            justify="center"
        )
        lbl_msg.pack(padx=20, pady=10)
        
        btn_cerrar = ctk.CTkButton(
            modal, text="Entendido, cerrar alerta", fg_color="#1E3E62", hover_color="#152B44",
            text_color="#FFFFFF", corner_radius=5,
            command=modal.destroy
        )
        btn_cerrar.pack(pady=(10, 20))

    # --- ACCIONES DE LOS BOTONES DE CONTROL GENERAL ---

    def action_iniciar(self):
        self.btn_iniciar.configure(state="disabled", fg_color="#F1F5F9", text_color="#94A3B8")
        self.btn_pausar.configure(state="normal", text="⏸  Pausar", fg_color="#FFFFFF", text_color="#1E293B")
        self.btn_detener.configure(state="normal", fg_color="#FFFFFF", text_color="#DC2626", border_color="#FCA5A5")
        self.status_satq_label.configure(text="Portal: ACTIVO", fg_color="#16A34A")

        # Desactivar controles de configuración y utilidades durante la ejecución del bot
        self.switch_omitir_generadas.configure(state="disabled")
        self.btn_select_excel.configure(state="disabled")
        self.btn_select_download.configure(state="disabled")
        self.btn_change_url.configure(state="disabled")
        self.btn_validar_pdfs.configure(state="disabled")

        # Leer configuración del switch
        solo_no_generadas = bool(self.switch_omitir_generadas.get())
        
        # Iniciar orquestador con la configuración
        self.orchestrator.iniciar(solo_no_generadas=solo_no_generadas)

    def action_pausar(self):
        if not self.orchestrator.is_paused:
            self.orchestrator.pausar()
            self.btn_pausar.configure(text="Reanudar Bot", fg_color="#DCFCE7", text_color="#15803D", border_color="#86EFAC")
        else:
            self.orchestrator.reanudar()
            self.btn_pausar.configure(text="⏸  Pausar", fg_color="#FFFFFF", text_color="#1E293B", border_color="#CBD5E1")

    def action_detener(self):
        self.orchestrator.detener()
        self.btn_detener.configure(state="disabled", border_color="#CBD5E1", text_color="#94A3B8")
        self.btn_pausar.configure(state="disabled")

    def action_restablecer_controles(self):
        """
        Restaura los botones de control a su estado inicial.
        """
        self.btn_iniciar.configure(state="normal", fg_color="#1E3E62", text_color="#FFFFFF")
        self.btn_pausar.configure(state="disabled", text="⏸  Pausar", fg_color="#FFFFFF", text_color="#1E293B", border_color="#CBD5E1")
        self.btn_detener.configure(state="disabled", fg_color="#FFFFFF", text_color="#1E293B", border_color="#CBD5E1")
        self.status_satq_label.configure(text="Portal: INACTIVO", fg_color="#4B6584")
        
        # Reactivar controles de configuración y utilidades
        self.switch_modo_autonomo.configure(state="normal")
        self.switch_omitir_generadas.configure(state="normal")
        self.btn_select_excel.configure(state="normal")
        self.btn_select_download.configure(state="normal")
        self.btn_change_url.configure(state="normal")
        self.btn_validar_pdfs.configure(state="normal")
        self._validar_rutas()
        self.btn_login_continuar.pack_forget()

        # Reactivar switches de configuración
        self.switch_modo_autonomo.configure(state="normal")
        self.switch_omitir_generadas.configure(state="normal")

    def action_toggle_modo_autonomo(self):
        """Callback al presionar el switch de modo autónomo para guardar inmediatamente en la persistencia."""
        modo = "autonomo" if self.switch_modo_autonomo.get() else "asistido"
        settings.set_modo_timbrado(modo)
        self._agregar_log_consola(f"[SISTEMA] Modo de timbrado cambiado a: {modo.upper()}", "INFO")

    def action_continuar_login(self):
        """
        Invoca la señal de que el login manual fue completado por el operador.
        """
        self.btn_login_continuar.pack_forget()
        self.orchestrator.notificar_login_completado()

        # Re‑validar rutas al volver a la UI
        self._validar_rutas()

    def action_aprobar_timbrar(self):
        """
        El operador aprobó los datos en el formulario: el bot puede proceder a timbrar.
        """
        self._agregar_log_consola("[VALIDACIÓN] ✅ Timbrado aprobado por el operador. Procediendo...", "INFO")
        self.btn_aprobar_timbrar.pack_forget()
        self.btn_cancelar_timbrar.pack_forget()
        self.orchestrator.notificar_timbrado_aprobado()

    def action_cancelar_timbrar(self):
        """
        El operador canceló el timbrado: el bot omitirá esta fila y continuará.
        """
        self._agregar_log_consola("[VALIDACIÓN] ❌ Timbrado cancelado por el operador. Fila marcada para revisión manual.", "WARNING")
        self.btn_aprobar_timbrar.pack_forget()
        self.btn_cancelar_timbrar.pack_forget()
        self.orchestrator.notificar_timbrado_cancelado()

    def action_abrir_excel(self):
        """
        Abre el archivo excel de trabajo directamente en Microsoft Excel en Windows de forma segura.
        """
        try:
            if os.path.exists(self.excel_path):
                os.startfile(self.excel_path)
                self._agregar_log_consola("[SISTEMA] [EXCEL] Abriendo archivo Optima_Capture_Bot.xlsx en Windows...", "INFO")
            else:
                self._agregar_log_consola("[SISTEMA] [ERROR] No se encuentra el archivo excel en la raíz.", "ERROR")
        except Exception as e:
            logger.error(f"No se pudo abrir el archivo Excel: {e}")

    def action_select_excel(self):
        """Permite al usuario seleccionar el archivo Excel origen."""
        archivo = filedialog.askopenfilename(
            title="Seleccionar archivo Excel",
            filetypes=[("Archivos Excel", "*.xlsx *.xls")]
        )
        if archivo:
            ruta_temporal = os.path.abspath(archivo)
            try:
                # Validar el RFC del catálogo antes de guardar de forma permanente
                catalog = cargar_catalog_rfc(ruta_temporal)
                rfc_valido, msg_err = es_rfc_permitido(catalog.get("rfc"))
                if not rfc_valido:
                    messagebox.showerror(
                        "RFC No Autorizado",
                        f"El archivo seleccionado contiene un RFC no válido:\n\n{msg_err}\n\nPor favor, seleccione un archivo autorizado."
                    )
                    self._agregar_log_consola(f"[SISTEMA] [ERROR] Selección cancelada: {msg_err}", "ERROR")
                    return

                self.excel_path = ruta_temporal
                settings.set_excel_path(self.excel_path)
                if self.orchestrator:
                    self.orchestrator.excel_path = self.excel_path
                self._agregar_log_consola(f"[SISTEMA] Ruta de Excel seleccionada: {self.excel_path}", "INFO")
                
                self.temp_catalog = catalog
                self.lbl_catalog_info.configure(
                    text=f"RFC: {catalog.get('rfc','')} | Razón Social: {catalog.get('razon_social','')[:18]}...\nCP: {catalog.get('cp','')}",
                    text_color="#64748B"
                )
                self._agregar_log_consola("[SISTEMA] Datos de catálogo cargados y validados correctamente.", "INFO")
            except Exception as e:
                messagebox.showerror(
                    "Error de Estructura",
                    f"No se pudo leer la estructura del catálogo del Excel:\n{e}"
                )
                self._agregar_log_consola(f"[SISTEMA] Error al cargar catálogo: {e}", "ERROR")
            self._validar_rutas()

    def action_select_download(self):
        """Permite al usuario seleccionar la carpeta donde se descargarán las facturas."""
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta de descargas")
        if carpeta:
            settings.set_download_dir(carpeta)
            self._agregar_log_consola(f"[SISTEMA] Carpeta de descargas seleccionada: {carpeta}", "INFO")
            self._validar_rutas()

    def action_validar_pdfs(self):
        """
        Ejecuta la validación de archivos PDF contra las referencias en el Excel de forma asíncrona.
        """
        ruta_excel = getattr(self, 'excel_path', '') or settings.get_excel_path()
        ruta_descarga = settings.get_download_dir()

        if not ruta_excel or not os.path.isfile(ruta_excel):
            messagebox.showerror("Error", "Debe seleccionar un archivo Excel válido primero.")
            return
        if not ruta_descarga or not os.path.isdir(ruta_descarga):
            messagebox.showerror("Error", "Debe seleccionar una carpeta de descargas válida primero.")
            return

        self._agregar_log_consola("[SISTEMA] [VALIDACIÓN-PDF] Iniciando validación de PDFs...", "INFO")
        
        # Desactivar botones de la interfaz gráfica durante el proceso
        self.btn_iniciar.configure(state="disabled")
        self.btn_select_excel.configure(state="disabled")
        self.btn_select_download.configure(state="disabled")
        self.btn_change_url.configure(state="disabled")
        self.btn_validar_pdfs.configure(state="disabled")
        
        # Ejecutar validación en un hilo separado para mantener la UI responsiva
        def _thread_val():
            try:
                from app.excel_handler import cargar_registros, colorear_celdas_validacion
                from app.pdf_validator import PDFValidator
                
                # Cargar registros desde Excel
                registros = cargar_registros(ruta_excel)
                if not registros:
                    self._agregar_log_consola("[SISTEMA] [VALIDACIÓN-PDF] No se encontraron registros en el Excel.", "WARNING")
                    return
                
                # Extraer referencias y mapear sus filas
                todas_referencias = [reg["referencia"] for reg in registros]
                referencias_ok_gen = [reg["referencia"] for reg in registros if reg["estado"] == "OK-GENERADA"]
                map_filas = {reg["referencia"]: reg["fila_excel"] for reg in registros}
                
                self._agregar_log_consola(f"[SISTEMA] [VALIDACIÓN-PDF] Analizando {len(referencias_ok_gen)} referencias en estado 'OK-GENERADA'...", "INFO")
                
                # Ejecutar análisis del validador de PDFs
                validator = PDFValidator(ruta_descarga)
                resultados, totales, extras = validator.run(referencias_ok_gen)
                
                total_refs, completos, incompletos, sin_descarga, cobertura = totales
                
                # Mapear colores para las celdas de las referencias procesadas
                mapeo_colores = {}
                for ref, estado in resultados.items():
                    fila = map_filas[ref]
                    if estado == "INCOMPLETO":
                        mapeo_colores[fila] = "AZUL"
                    elif estado == "NO_DESCARGADO":
                        mapeo_colores[fila] = "AMARILLO"
                    else:
                        mapeo_colores[fila] = None # Limpiar relleno
                
                # Aplicar colores en el Excel
                colorear_celdas_validacion(ruta_excel, mapeo_colores)
                
                # Reportar resultados en la consola de logs
                self._agregar_log_consola("\n--- REPORTE DE VALIDACIÓN DE PDFs ---", "INFO")
                self._agregar_log_consola(f"  · Total referencias 'OK-GENERADA': {len(referencias_ok_gen)}", "INFO")
                self._agregar_log_consola(f"  · Referencias completas (2 PDFs): {completos}", "INFO")
                self._agregar_log_consola(f"  · Referencias incompletas (1 PDF) [AZUL]: {incompletos}", "WARNING")
                self._agregar_log_consola(f"  · Referencias sin archivos (0 PDFs) [AMARILLO]: {sin_descarga}", "ERROR")
                
                # Reportar archivos extras
                if extras:
                    self._agregar_log_consola("\n[SISTEMA] [VALIDACIÓN-PDF] ARCHIVOS EXTRAS DETECTADOS EN LA CARPETA:", "WARNING")
                    for extra in extras:
                        self._agregar_log_consola(f"  · {extra}", "WARNING")
                else:
                    self._agregar_log_consola("\n[SISTEMA] [VALIDACIÓN-PDF] No se detectaron archivos extras.", "INFO")
                
                self._agregar_log_consola("-------------------------------------\n", "INFO")
                
                # Mensaje visual de finalización
                messagebox.showinfo(
                    "Validación Finalizada",
                    f"Validación de PDFs completada.\n\n"
                    f"Total OK-GENERADA: {len(referencias_ok_gen)}\n"
                    f"Completas: {completos}\n"
                    f"Incompletas (Azul): {incompletos}\n"
                    f"Sin descargas (Amarillo): {sin_descarga}\n"
                    f"Archivos extras: {len(extras)}"
                )
                
            except Exception as thread_err:
                self._agregar_log_consola(f"[SISTEMA] [ERROR-VALIDACIÓN] Ocurrió un error: {thread_err}", "ERROR")
                messagebox.showerror("Error de Validación", f"Ocurrió un error durante la validación:\n{thread_err}")
            finally:
                # Volver a activar todos los botones e invocar validar_rutas para ajustar estados iniciales
                self.btn_select_excel.configure(state="normal")
                self.btn_select_download.configure(state="normal")
                self.btn_change_url.configure(state="normal")
                self.btn_validar_pdfs.configure(state="normal")
                self._validar_rutas()
                
        threading.Thread(target=_thread_val, daemon=True).start()

    def action_change_url(self):
        """Permite al usuario cambiar la URL del portal SATQ en caso de que haya sido modificada."""
        from tkinter import simpledialog
        current_url = settings.get_satq_url()
        new_url = simpledialog.askstring("Cambiar URL SATQ", "Ingrese la nueva URL del portal SATQ:", initialvalue=current_url)
        if new_url:
            settings.set_satq_url(new_url)
            self._agregar_log_consola(f"[SISTEMA] URL del portal SATQ actualizada a: {new_url}", "INFO")
            self._agregar_log_consola("[SISTEMA] Reinicie el bot para cargar la nueva URL.", "WARNING")

    def _validar_rutas(self):
        """Habilita el botón 'Iniciar Bot' sólo si Excel y carpeta de descargas están configurados y el RFC es válido."""
        ruta_excel = getattr(self, 'excel_path', '') or settings.get_excel_path()
        ruta_descarga = settings.get_download_dir()
        
        excel_ok = bool(ruta_excel and os.path.isfile(ruta_excel))
        descarga_ok = bool(ruta_descarga and os.path.isdir(ruta_descarga))
        
        if excel_ok and descarga_ok:
            try:
                catalog = cargar_catalog_rfc(ruta_excel)
                rfc_valido, msg_err = es_rfc_permitido(catalog.get("rfc"))
                
                if rfc_valido:
                    if hasattr(self, 'btn_iniciar'):
                        self.btn_iniciar.configure(state="normal", text="▶  Iniciar Bot", fg_color="#1E3E62")
                    if hasattr(self, 'lbl_catalog_info'):
                        self.lbl_catalog_info.configure(
                            text=f"RFC: {catalog.get('rfc','')} | Razón Social: {catalog.get('razon_social','')[:18]}...\nCP: {catalog.get('cp','')}",
                            text_color="#64748B"
                        )
                else:
                    if hasattr(self, 'btn_iniciar'):
                        self.btn_iniciar.configure(state="disabled", text="▶  Iniciar Bot (RFC No Autorizado)")
                    if hasattr(self, 'lbl_catalog_info'):
                        self.lbl_catalog_info.configure(
                            text=f"⚠️ {msg_err}\nSeleccione un archivo autorizado para comenzar.",
                            text_color="#E11D48"
                        )
            except Exception as ex:
                if hasattr(self, 'btn_iniciar'):
                    self.btn_iniciar.configure(state="disabled", text="▶  Iniciar Bot (Error Catálogo)")
                if hasattr(self, 'lbl_catalog_info'):
                    self.lbl_catalog_info.configure(
                        text=f"⚠️ Error al leer catálogo: {ex}",
                        text_color="#E11D48"
                    )
        else:
            if hasattr(self, 'btn_iniciar'):
                self.btn_iniciar.configure(state="disabled")
            
            if not excel_ok:
                if hasattr(self, 'btn_iniciar'):
                    self.btn_iniciar.configure(text="▶  Iniciar Bot (Falta Excel)")
                if hasattr(self, 'lbl_catalog_info'):
                    self.lbl_catalog_info.configure(
                        text="⚠️ Archivo Excel no encontrado.\nSeleccione un archivo válido para comenzar.",
                        text_color="#E11D48"
                    )
            elif not descarga_ok:
                if hasattr(self, 'btn_iniciar'):
                    self.btn_iniciar.configure(text="▶  Iniciar Bot (Falta Descargas)")
                if hasattr(self, 'lbl_catalog_info'):
                    self.lbl_catalog_info.configure(
                        text="⚠️ Carpeta de descargas inválida.\nSeleccione una carpeta para comenzar.",
                        text_color="#D97706"
                    )

    # --- ACCIONES DEL PANEL EXCLUSIVO DE GESTIÓN DE ERRORES ---

    def action_ver_screenshot(self):
        """
        Abre el visor de imágenes de Windows con la captura de pantalla de evidencia.
        """
        try:
            if self.orchestrator.scraper:
                files = os.listdir(SCREENSHOTS_DIR)
                if files:
                    files.sort(key=lambda x: os.path.getmtime(SCREENSHOTS_DIR / x), reverse=True)
                    img_path = os.path.abspath(SCREENSHOTS_DIR / files[0])
                    os.startfile(img_path)
                    self._agregar_log_consola(f"[SISTEMA] Abriendo captura de evidencia: {img_path}", "INFO")
                else:
                    self._agregar_log_consola("[SISTEMA] No hay capturas disponibles en la carpeta de soporte.", "WARNING")
        except Exception as e:
            logger.error(f"Error al abrir la captura de pantalla: {e}")

    def action_reintentar_registro(self):
        self.btn_ver_screenshot.configure(state="normal")
        self._agregar_log_consola("[SISTEMA] Reintento manual activado. Se ha restablecido el estado a PENDIENTE para su revaluación.", "INFO")
        self.btn_reintentar_registro.configure(state="disabled")

    def action_omitir_registro(self):
        self._agregar_log_consola("[SISTEMA] Registro omitido formalmente por el operador. Guardando en Excel como OMITIDO.", "WARNING")
        self.btn_reintentar_registro.configure(state="disabled")
        self.btn_omitir_registro.configure(state="disabled")

    def action_revision_manual(self):
        self._agregar_log_consola("[SISTEMA] Registro clasificado como REQUIERE_REVISION en Excel.", "WARNING")
        self.btn_reintentar_registro.configure(state="disabled")
        self.btn_revision_manual.configure(state="disabled")

    def _establecer_icono(self):
        """
        Carga el archivo ico/cupture_bot.png y lo asigna como icono de ventana.
        Es seguro frente a fallos y compatible con el empaquetado de PyInstaller.
        """
        import sys
        try:
            # Obtener ruta absoluta compatible con PyInstaller
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.abspath(".")
            
            icon_path = os.path.join(base_path, "ico", "cupture_bot.ico")
            
            if os.path.exists(icon_path):
                img = tk.PhotoImage(file=icon_path)
                self.iconphoto(True, img)
                logger.info(f"Icono cargado exitosamente desde: {icon_path}")
            else:
                logger.warning(f"No se encontró el icono en la ruta: {icon_path}")
        except Exception as icon_err:
            logger.warning(f"No se pudo cargar el icono de la ventana: {icon_err}")

