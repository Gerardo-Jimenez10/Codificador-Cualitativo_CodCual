import tkinter as tk
from tkinter import filedialog, messagebox, Menu, colorchooser, simpledialog
from tkinter import font
from tkinter import PhotoImage
from PIL import Image, ImageTk
import textwrap
import pickle
import docx
import fitz  # PyMuPDF para manejo de PDF
import os
import uuid  # Para generar identificadores únicos

# --- IMPORTACIÓN Y MANEJO DE NLTK (PROCESAMIENTO DE LENGUAJE NATURAL) ---
import nltk
try:
    # Se intenta descargar los recursos necesarios para tokenización de texto de manera silenciosa
    nltk.download('punkt_tab', quiet=True)
    nltk.download('punkt', quiet=True)
except Exception:
    # Si falla la descarga, se continúa la ejecución (se manejará el error posteriormente)
    pass 

# --- HABILITAR ALTA RESOLUCIÓN (DPI AWARENESS) PARA SISTEMAS WINDOWS ---
try:
    from ctypes import windll
    # Se configura el proceso para reconocer la escala de DPI del monitor y evitar borrosidad
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# --- FUNCIÓN GLOBAL PARA CARGAR CONTENIDO DE ARCHIVOS ---
def cargar_contenido(ruta_archivo):
    # Se verifica si la extensión del archivo es .txt
    if ruta_archivo.lower().endswith('.txt'):
        # Se abre el archivo en modo lectura con codificación UTF-8
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            contenido = archivo.read()
    # Se verifica si la extensión del archivo es .docx
    elif ruta_archivo.lower().endswith('.docx'):
        # Se utiliza la librería docx para leer el documento
        doc = docx.Document(ruta_archivo)
        # Se unen los párrafos extraídos con saltos de línea
        contenido = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
    # Se verifica si la extensión del archivo es .pdf
    elif ruta_archivo.lower().endswith('.pdf'):
        # Se utiliza la librería fitz (PyMuPDF) para abrir el PDF
        pdf_doc = fitz.open(ruta_archivo)
        contenido = ''
        # Se itera sobre cada página del PDF para extraer el texto
        for page_num in range(pdf_doc.page_count):
            page = pdf_doc[page_num]
            contenido += page.get_text()
    else:
        # Se lanza una excepción si el formato no es compatible
        raise ValueError(
            "Formato de archivo no compatible. Utilice archivos .txt, .docx o .pdf.")
    # Se retorna el contenido extraído como cadena de texto
    return contenido


# --- CLASE PARA LA CREACIÓN DE TOOLTIPS (VENTANAS EMERGENTES) ---
class Tooltip:
    def __init__(self, widget, text):
        # Se inicializa la referencia al widget padre y el texto a mostrar
        self.widget = widget
        self.text = text
        self.tooltip_window = None

    def show_tooltip(self, event, tag_name):
        # Se calculan las coordenadas para mostrar el tooltip cerca del cursor (+10 píxeles)
        x, y = event.x_root + 10, event.y_root + 10

        # Se crea una ventana secundaria (Toplevel) asociada al widget
        self.tooltip_window = tk.Toplevel(self.widget)
        # Se elimina la decoración de ventana (bordes, título)
        self.tooltip_window.wm_overrideredirect(True)
        # Se establece la posición en pantalla
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        # Se crea la etiqueta que contiene el texto del tooltip
        label = tk.Label(
            self.tooltip_window,
            text=str(self.text),
            justify='left',
            background='#FFFF66',  # Fondo amarillo claro
            relief='solid',
            borderwidth=1,
            font=("arial", 11, "bold", "italic")
        )
        # Se empaqueta la etiqueta con relleno interno
        label.pack(ipadx=5, ipady=2)

        # Se cambia el cursor del widget padre para indicar interactividad
        self.widget.config(cursor="circle")

    def hide_tooltip(self, _):
        # Se verifica si la ventana del tooltip existe
        if self.tooltip_window:
            # Se destruye la ventana para ocultarla
            self.tooltip_window.destroy()
            self.tooltip_window = None

        # Se restaura el cursor del widget a su estado normal (cadena vacía)
        self.widget.config(cursor="")

    def update_position(self, event):
        # Se actualiza la posición del tooltip si el mouse se mueve dentro del área
        if self.tooltip_window:
            x = event.x_root + 10
            y = event.y_root + 10
            self.tooltip_window.geometry(f"+{x}+{y}")

# --- FUNCIÓN AUXILIAR PARA RUTAS RELATIVAS (COMPATIBILIDAD CON PYINSTALLER) ---
def ruta_relativa(ruta):
    import sys, os
    # Se verifica si la aplicación está empaquetada (sys._MEIPASS existe en PyInstaller)
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, ruta)
    # Si no está empaquetada, se retorna la ruta original
    return ruta

# --- CLASE PRINCIPAL DE LA APLICACIÓN ---
class EtiquetadoApp:
    def __init__(self, raiz):
        # Se inicializa la clase padre (aunque no hereda explícitamente de otra clase propia)
        super().__init__()
        self.raiz = raiz
        # Se establece el título de la ventana principal
        self.raiz.title('"Codificador Cualitativo"')
        # Se configura el color de fondo de la ventana principal
        self.raiz.configure(bg="green")
        # Se inicia la ventana maximizada ("zoomed" funciona en Windows)
        self.raiz.state("zoomed")
        # Se establece un tamaño mínimo para evitar deformaciones excesivas
        self.raiz.minsize(800, 600)

        # --- VARIABLES DE CONTROL TKINTER ---
        self.palabras_clave_var = tk.StringVar()
        self.etiqueta_var = tk.StringVar()

        # --- ESTRUCTURAS DE DATOS ---
        # Diccionario para gestionar múltiples archivos abiertos y sus estados
        self.archivos_abiertos = {}
        # Diccionario para mapear etiquetas de texto a objetos Tooltip
        self.tooltips_asignados = {}
        # Lista para mantener el historial de archivos recientes
        self.historial_archivos = []
        # Diccionario para persistencia de colores asociados a etiquetas
        self.color_tooltips = {}
        # Diccionario para el índice de navegación entre coincidencias de búsqueda
        self.indice_navegacion = {} 

        # Variables de estado del archivo actual
        self.ruta = None
        self.contenido = None

        # --- CONFIGURACIÓN DEL MENÚ PRINCIPAL ---
        self.barraMenu = Menu(self.raiz)
        # Se asigna la barra de menú a la ventana raíz
        self.raiz.configure(menu=self.barraMenu)

        # --- CARGA DE ÍCONOS Y RECURSOS GRÁFICOS ---
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ruta_base = ruta_relativa(base_dir)
        icono_ruta = os.path.join(ruta_base, "Logo.png")

        # Se intenta cargar el ícono de la ventana
        try:
            imagen_icono = Image.open(icono_ruta)
            self.icono_tk = ImageTk.PhotoImage(imagen_icono)
            self.raiz.iconphoto(True, self.icono_tk)
        except Exception:
            pass # Si falla la carga, se ignora el error

        # Ruta al directorio de íconos
        ruta_iconos = ruta_relativa(os.path.join(base_dir, "Iconos"))

        # Función local para cargar imágenes de manera segura
        def cargar_icono(nombre):
            try:
                return PhotoImage(file=os.path.join(ruta_iconos, nombre))
            except Exception:
                return None

        # Se cargan los íconos para las opciones del menú
        self.icono_importar  = cargar_icono("importar.png")
        self.icono_guardado  = cargar_icono("guardar.png")
        self.icono_salir     = cargar_icono("salir.png")
        self.icono_limpiar   = cargar_icono("limpiar.png")
        self.icono_info      = cargar_icono("información.png")
        self.icono_eliminar  = cargar_icono("eliminar.png")
        self.icono_anexar    = cargar_icono("anexar.png")
        self.icono_codificar = cargar_icono("codificar.png")
        self.icono_remover   = cargar_icono("remover.png")

        # --- SUBMENÚ ARCHIVO ---
        self.menu_desplegable = Menu(self.barraMenu, tearoff=0)
        self.menu_desplegable.add_command(label="Importar Archivo", image=self.icono_importar, compound='left', font=(
            "arial", 12, "bold"), foreground="red", command=self.importar_archivo)
        self.menu_desplegable.add_separator()
        self.menu_desplegable.add_command(label="Guardar Codificado", image=self.icono_guardado, compound='left', font=(
            "arial", 12, "bold"), foreground="brown", command=self.guardar_codificado)
        self.menu_desplegable.add_separator()
        self.menu_desplegable.add_command(label="Salir", image=self.icono_salir, compound='left', font=(
            "arial", 12, "bold"), foreground="Green", command=self.salir_programa)

        # --- SUBMENÚ EDICIÓN ---
        self.edicionMenu = Menu(self.barraMenu, tearoff=0)
        self.edicionMenu.add_command(label="Limpiar Citas del Código", image=self.icono_limpiar, compound='left', font=(
            "arial", 12, "bold"), foreground="navy blue", command=self.limpiar_contenido)

        # --- SUBMENÚ INFORMACIÓN ---
        self.menu_información = Menu(self.barraMenu, tearoff=0)
        self.menu_información.add_command(
            label="Acerca de...", compound='left', image=self.icono_info, font=(
                "arial", 12, "bold"), foreground="purple", command=self.mostrar_informacion)

        # --- SUBMENÚ HISTORIAL ---
        self.menu_archivos_abiertos = Menu(self.barraMenu, tearoff=0)

        # Se agregan las cascadas a la barra de menú principal
        self.barraMenu.add_cascade(label="Archivo", menu=self.menu_desplegable)
        self.barraMenu.add_cascade(label="Edición", menu=self.edicionMenu)
        self.barraMenu.add_cascade(label="Historial", menu=self.menu_archivos_abiertos)
        self.barraMenu.add_cascade(label="Información", menu=self.menu_información)

        # Título central de la aplicación en la interfaz
        tk.Label(raiz, text="CodCual", font=("Magneto", 32, "bold"),
                 fg="yellow", bg="green").grid(row=0, column=2, padx=(20, 20), pady=(8, 40))


        # =========================================================================================
        # SECCIÓN DE CONTROL DE TAMAÑOS Y DISTRIBUCIÓN DE PANELES (FRAMES DE LA INTERFAZ)
        # =========================================================================================
        
        # -------------------- ÁREA 1: PANEL IZQUIERDO (LISTA DE CÓDIGOS) --------------------
        
        # Etiqueta de encabezado para el panel izquierdo
        tk.Label(raiz, text="Lista de Codificaciones Realizadas", font=("arial", 12, "bold"), bg="cyan").grid(
            row=4, column=0, columnspan=2, padx=(8, 0), pady=(8, 0), sticky='ew')

        # --- FRAME CONTENEDOR PARA MANEJAR SCROLL HORIZONTAL Y VERTICAL ---
        frame_lista = tk.Frame(raiz)
        frame_lista.grid(row=5, column=0, pady=(0, 8), padx=(8, 0), sticky='nsew')
        
        # Configuración de pesos del frame contenedor
        frame_lista.grid_rowconfigure(0, weight=1)
        frame_lista.grid_columnconfigure(0, weight=1)

        # Widget de Texto (Lista): 
        # IMPORTANTE: wrap="none" es vital para que funcione el scroll horizontal
        self.lista_etiquetado = tk.Text(
            frame_lista, wrap="none", width=30, height=24, bg="#FFFFCC")
        self.lista_etiquetado.grid(row=0, column=0, sticky='nsew')
        
        # Bloqueo de edición manual en la lista de códigos
        self.lista_etiquetado.bind("<Key>", lambda e: "break")       
        self.lista_etiquetado.bind("<BackSpace>", lambda e: "break") 
        self.lista_etiquetado.bind("<Delete>", lambda e: "break")    
        self.lista_etiquetado.bind("<<Paste>>", lambda e: "break")   
        self.lista_etiquetado.bind("<<Cut>>", lambda e: "break")     
        self.lista_etiquetado.bind("<<Clear>>", lambda e: "break")    
        self.lista_etiquetado.bind("<Control-v>", lambda e: "break") 
        self.lista_etiquetado.bind("<Control-x>", lambda e: "break")  
        self.lista_etiquetado.bind("<Button-1>", lambda e: "break")   
        self.lista_etiquetado.bind("<B1-Motion>", lambda e: "break")

        # Barra de desplazamiento VERTICAL
        scrollVertical3 = tk.Scrollbar(
            frame_lista, command=self.lista_etiquetado.yview)
        scrollVertical3.grid(row=0, column=1, sticky="ns")
        self.lista_etiquetado.config(yscrollcommand=scrollVertical3.set)

        # --- Barra de desplazamiento HORIZONTAL (Dinámica) ---
        self.scrollHorizontal = tk.Scrollbar(
            frame_lista, orient="horizontal", command=self.lista_etiquetado.xview)
        
        # Inicialmente la colocamos en la grilla, pero será gestionada por 'actualizar_scroll_horizontal_codigos'
        self.scrollHorizontal.grid(row=1, column=0, sticky="ew")
        self.lista_etiquetado.config(xscrollcommand=self.scrollHorizontal.set)
        
        # Eventos para detectar cambios de tamaño y activar/desactivar la barra
        self.lista_etiquetado.bind("<Configure>", lambda e: self.actualizar_scroll_horizontal_codigos())


        # -------------------- ÁREA 2: PANEL CENTRAL (TEXTO ORIGINAL) --------------------
        
        # Etiqueta de encabezado para el panel central
        tk.Label(raiz, text="Texto", font=("arial", 12, "bold"), bg="#99FF00").grid(
            row=4, column=2, columnspan=2, pady=(8, 0), padx=(8, 0), sticky='ew')

        # Widget de Texto (Central)
        self.texto_original = tk.Text(raiz, wrap=tk.WORD, width=77, height=23, font=(
            "Arial", 13))   
        self.texto_original.grid(row=5, column=2, padx=(
            8, 0), pady=(0, 8), sticky='nsew')

        # Barra de desplazamiento para el texto original
        scrollVertical1 = tk.Scrollbar(raiz, command=self.texto_original.yview)
        scrollVertical1.grid(row=5, column=3, pady=(0, 8), sticky="nsew")
        self.texto_original.config(yscrollcommand=scrollVertical1.set)


        # -------------------- ÁREA 3: PANEL DERECHO (CITAS DEL CÓDIGO) --------------------
        
        # Etiqueta de encabezado para el panel derecho
        tk.Label(raiz, text="Citas del Código", font=("arial", 12, "bold"), bg="#FF93F2").grid(
            row=4, column=4, columnspan=2, pady=(8, 0), padx=(8, 8), sticky='ew')

        # Widget de Texto (Derecho)
        self.texto_etiquetado = tk.Text(
            raiz, wrap=tk.WORD, width=30, height=23, font=("Arial", 13))
        self.texto_etiquetado.grid(row=5, column=4, padx=(
            8, 0), pady=(0, 8), sticky='nsew')
        self.texto_etiquetado.configure(bg="#FFFFCC")

        # Barra de desplazamiento para las citas
        scrollVertical2 = tk.Scrollbar(
            raiz, command=self.texto_etiquetado.yview)
        scrollVertical2.grid(row=5, column=5, pady=(0, 8),
                             padx=(0, 8), sticky="nsew")
        self.texto_etiquetado.config(yscrollcommand=scrollVertical2.set)


        # -------------------- CONTROL DE EXPANSIÓN (WEIGHTS) --------------------
        
        raiz.grid_rowconfigure(5, weight=1)        # Permite que la fila de los textos crezca verticalmente
        raiz.grid_columnconfigure(0, weight=1)     # Expansión del Panel Izquierdo (Lista)
        raiz.grid_columnconfigure(2, weight=1)     # Expansión del Panel Central (Texto Original)
        raiz.grid_columnconfigure(4, weight=1)     # Expansión del Panel Derecho (Citas)

        # =========================================================================================

        # --- INICIALIZACIÓN DE VARIABLES DE ESTADO ---
        self.ruta = None
        self.contenido = None
        self.tokens = None
        self.sentencias = None
        self.etiqueta_actual = None
        self.parrafos_etiquetados = []
        self.indices_etiquetados = []
        self.etiquetas_asignadas = []

        # Se actualiza la vista de la lista de etiquetas
        self.actualizar_lista_etiquetado()

        # --- RECUPERACIÓN DE DATOS GUARDADOS (PERSISTENCIA) ---
        datos_guardados = {}
        try:
            with open("datos_codificacion.pkl", "rb") as archivo_datos:
                datos_guardados = pickle.load(archivo_datos)
        except (FileNotFoundError, Exception):
            datos_guardados = {}

        # Se cargan los datos recuperados en las variables de instancia
        self.historial_archivos = datos_guardados.get("historial_archivos", [])
        self.archivos_abiertos = datos_guardados.get("archivos_abiertos", {})
        self.etiquetas_asignadas = datos_guardados.get("etiquetas_asignadas", [])
        self.parrafos_etiquetados = datos_guardados.get("parrafos_etiquetados", [])
        self.color_tooltips = datos_guardados.get("color_tooltips", {})
        self.indice_navegacion = datos_guardados.get("indice_navegacion", {})

        # Validación de estructuras de tokens y sentencias
        self.tokens = datos_guardados.get("tokens", [])
        if not isinstance(self.tokens, list):
            self.tokens = list(self.tokens) if self.tokens else []

        self.sentencias = datos_guardados.get("sentencias", [])
        if not isinstance(self.sentencias, list):
            self.sentencias = list(self.sentencias) if self.sentencias else []

        # Se actualiza el menú de historial con los datos cargados
        self.actualizar_menu_historial()

        # --- RESTAURACIÓN DE LA ÚLTIMA SESIÓN ---
        if self.archivos_abiertos:
            nombre_archivo, datos = next(iter(self.archivos_abiertos.items()))
            self.contenido = datos.get("contenido", "")
            # Intento de re-tokenización
            try:
                self.tokens = nltk.sent_tokenize(self.contenido)
                self.sentencias = nltk.sent_tokenize(self.contenido)
            except:
                 # Fallback manual si NLTK falla
                 self.tokens = self.contenido.split('.')
                 self.sentencias = self.contenido.split('.')

            self.mostrar_contenido_original()
            
            # Restauración de la ruta del archivo
            for h in self.historial_archivos:
                if h["nombre"] == nombre_archivo:
                    self.ruta = h["ruta"]
                    break

            # Restauración visual de los subrayados y tooltips
            for sub in datos.get("subrayados", []):
                tag_name = sub["tag"]
                start, end = sub["start"], sub["end"]
                color = sub["color"]
                etiqueta = sub["etiqueta"]

                # Recreación del tag en el widget Text
                self.texto_original.tag_add(tag_name, start, end)
                self.texto_original.tag_configure(
                    tag_name, underline=True, font=("Arial", 13, "bold"), foreground=color
                )

                # Recreación del Tooltip asociado
                tooltip = Tooltip(self.texto_original, etiqueta)
                self.texto_original.tag_bind(tag_name, "<Enter>", lambda e, t=tooltip, tg=tag_name: t.show_tooltip(e, tg))
                self.texto_original.tag_bind(tag_name, "<Leave>", tooltip.hide_tooltip)
                self.texto_original.tag_bind(tag_name, "<Motion>", tooltip.update_position)

            # Asegurar que la selección esté siempre visible tras cargar
            self.texto_original.tag_raise("sel")
        
        self.actualizar_lista_etiquetado()

        # --- EVENTOS DEL MOUSE ---
        # Se asocia el movimiento del mouse para cambiar el cursor sobre etiquetas
        self.texto_original.bind(
            "<Motion>", self.cambiar_cursor_segun_posicion)

        # --- MENÚ CONTEXTUAL (CLIC DERECHO) ---
        self.menu_contextual_texto_original = Menu(
            self.texto_original, tearoff=0)
        self.menu_contextual_texto_original.add_command(label="Codificar", image=self.icono_codificar, compound='left', font=(
            "arial", 12, "bold"), foreground="purple", command=self.etiquetar_fragmento)
        self.menu_contextual_texto_original.add_separator()
        self.menu_contextual_texto_original.add_command(label="Remover Codificado", image=self.icono_remover, compound='left', font=(
            "arial", 12, "bold"), foreground="red", command=self.quitar_subrayado)
        self.texto_original.bind(
            "<Button-3>", self.mostrar_menu_contextual_texto_original)

    # --- MÉTODO PARA MOSTRAR INFORMACIÓN DEL DESARROLLADOR ---
    def mostrar_informacion(self):
        messagebox.showinfo("Acerca de...",
                            "          Aplicación desarrollada en Python.\n\n"
                            "                  Derechos reservados®\n\n"
                            '         "GERARDO HERNÁNDEZ JIMÉNEZ"\n\n'
                            "   Egresado de la Licenciatura en Informática.\n\n"
                            "        Centro Universitario UAEM Texcoco.\n\n"
                            " Universidad Autónoma del Estado de México.")

    # --- MÉTODO PARA DESPLEGAR EL MENÚ CONTEXTUAL ---
    def mostrar_menu_contextual_texto_original(self, event):
        self.menu_contextual_texto_original.post(event.x_root, event.y_root)

    # --- MÉTODO PARA REGISTRAR UN ARCHIVO EN EL SISTEMA INTERNO ---
    def agregar_archivo_abierto(self, nombre_archivo, contenido):
        if nombre_archivo not in self.archivos_abiertos:
            self.archivos_abiertos[nombre_archivo] = {
                "contenido": contenido,
                "subrayados": []
            }
            # Se agrega la entrada al menú de historial
            self.menu_archivos_abiertos.add_command(
                label=nombre_archivo,
                command=lambda nombre=nombre_archivo: self.cambiar_archivo(nombre)
            )

    # --- MÉTODO PARA CAMBIAR ENTRE ARCHIVOS CARGADOS ---
    def cambiar_archivo(self, nombre_archivo):
        # 1. Se guarda el estado (subrayados) del archivo actual antes de cambiar
        self.guardar_subrayados()

        if nombre_archivo in self.archivos_abiertos:
            datos = self.archivos_abiertos[nombre_archivo]
            
            # Búsqueda de la ruta completa en el historial
            encontrado = False
            for h in self.historial_archivos:
                if h["nombre"] == nombre_archivo:
                    self.ruta = h["ruta"]
                    encontrado = True
                    break
            if not encontrado:
                self.ruta = os.path.abspath(nombre_archivo) 

            # Carga del contenido del nuevo archivo seleccionado
            self.contenido = datos.get("contenido", "")
            try:
                self.tokens = nltk.sent_tokenize(self.contenido)
                self.sentencias = nltk.sent_tokenize(self.contenido)
            except:
                self.tokens = self.contenido.split('.')
                self.sentencias = self.contenido.split('.')

            self.mostrar_contenido_original()

            # Restauración de etiquetas visuales y tooltips
            for subrayado in datos.get("subrayados", []):
                tag_name = subrayado['tag']
                start = subrayado['start']
                end = subrayado['end']
                color = subrayado['color']
                etiqueta = subrayado['etiqueta']

                self.texto_original.tag_add(tag_name, start, end)
                self.texto_original.tag_configure(
                    tag_name, underline=True, font=("Arial", 13, "bold"), foreground=color
                )

                tooltip = Tooltip(self.texto_original, etiqueta)
                self.texto_original.tag_bind(tag_name, "<Enter>", lambda event, tooltip=tooltip, tag_name=tag_name: tooltip.show_tooltip(event, tag_name))
                self.texto_original.tag_bind(tag_name, "<Leave>", tooltip.hide_tooltip)
                self.texto_original.tag_bind(tag_name, "<Motion>", tooltip.update_position)

            # Se asegura la visibilidad de selección al cambiar archivo
            self.texto_original.tag_raise("sel")

    # --- MÉTODO PARA IMPORTAR NUEVOS ARCHIVOS ---
    def importar_archivo(self):
        # Diálogo de sistema para seleccionar archivo
        self.ruta = filedialog.askopenfilename(title="Importar Archivo", filetypes=[
                                               ("Todos los archivos", "*.*")])
        if self.ruta:
            self.contenido = cargar_contenido(self.ruta)
            
            # Proceso de tokenización
            try:
                self.tokens = nltk.sent_tokenize(self.contenido)
                self.sentencias = nltk.sent_tokenize(self.contenido)
            except (LookupError, Exception):
                self.tokens = self.contenido.replace('\n', ' ').split('.')
                self.sentencias = self.contenido.replace('\n', ' ').split('.')
                self.tokens = [t + '.' for t in self.tokens if t.strip()]
                self.sentencias = [s + '.' for s in self.sentencias if s.strip()]

            self.mostrar_contenido_original()
            
            # Configuración de alto contraste para selección de texto
            self.texto_original.tag_configure("sel", background="#0078D7", foreground="white")
            self.texto_original.tag_raise("sel")

            nombre_archivo = os.path.basename(self.ruta)
            self.agregar_archivo_abierto(nombre_archivo, self.contenido)

            # Registro en historial, evitando duplicados
            registro = {"nombre": nombre_archivo, "ruta": self.ruta}
            self.historial_archivos = [
                r for r in self.historial_archivos if r["ruta"] != self.ruta
            ]
            self.historial_archivos.append(registro)

            self.actualizar_menu_historial()

    # --- MÉTODO PARA RESTAURAR CURSOR POR DEFECTO ---
    def restaurar_cursor(self, event):
        event.widget.config(cursor="")

    # --- MÉTODO PARA ACTUALIZAR EL MENÚ DE HISTORIAL ---
    def actualizar_menu_historial(self):
        self.menu_archivos_abiertos.delete(0, tk.END)

        if not self.archivos_abiertos:
            self.menu_archivos_abiertos.add_command(
                label="(Vacío)",
                state="disabled",
                font=("Arial", 11)
            )
            return

        for nombre in self.archivos_abiertos.keys():
            self.menu_archivos_abiertos.add_command(
                label=nombre,
                font=("Arial", 11),
                command=lambda n=nombre: self.cambiar_archivo(n)
            )

    # --- MÉTODO PARA DETECTAR HOVER SOBRE ETIQUETAS ---
    def cambiar_cursor_segun_posicion(self, event):
        x, y = event.x, event.y
        # Se verifica si hay tags en la posición del mouse
        tags = self.texto_original.tag_names("@{},{}".format(x, y))
        # Si alguno de los tags es una etiqueta de color, cambia el cursor
        if any(tag.startswith("Color_") for tag in tags):
            self.texto_original.config(cursor="circle")
        else:
            self.texto_original.config(cursor="xterm")

    # --- MÉTODO PRINCIPAL DE CODIFICACIÓN (ETIQUETADO) ---
    def etiquetar_fragmento(self):
        # Diálogo para ingresar el nombre del código
        etiqueta = simpledialog.askstring("Codificar", "Escribe un Código:")
        if etiqueta:
            # Selección de color
            color_subrayado = self.elegir_color_subrayado()

            # Validación: Si no selecciona color (cancela), se detiene el proceso
            if not color_subrayado:
                return 

            self.etiqueta_actual = etiqueta

            # -------------------------------------------------------------------------
            # LOGICA DE ESPACIADO Y SEPARACIÓN ENTRE BLOQUES DE CÓDIGOS (AJUSTADO)
            # -------------------------------------------------------------------------
            
            # Obtenemos el contenido actual para decidir los saltos de línea
            contenido_actual_texto = self.texto_etiquetado.get("1.0", tk.END).strip()
            
            if not contenido_actual_texto:
                 # CASO 1: Pantalla vacía (Primer fragmento) -> Solo 1 salto de línea
                 self.texto_etiquetado.insert(tk.END, "\n")
            
            else:
                 # Escaneo inverso para encontrar el último código insertado en el widget
                 ultimo_codigo_nombre = ""
                 content_raw = self.texto_etiquetado.get("1.0", tk.END)
                 
                 # Extraemos el texto del último "bloque" visible
                 bloques = content_raw.split(">>>(")
                 if len(bloques) > 1:
                     # El último bloque añadido
                     ultimo_bloque = bloques[-1]
                     # Extraer nombre hasta )<<<
                     if ")<<<" in ultimo_bloque:
                         ultimo_codigo_nombre = ultimo_bloque.split(")<<<")[0]

                 # Aplicar reglas de salto según coincidencia
                 if ultimo_codigo_nombre == etiqueta:
                     # CASO 2: Mismo código -> 1 salto de línea (estándar)
                     self.texto_etiquetado.insert(tk.END, "\n")
                 else:
                     # CASO 3: Códigos distintos -> 2 saltos de línea (REQUERIDO)
                     self.texto_etiquetado.insert(tk.END, "\n\n")

            # -------------------------------------------------------------------------

            # Inserción visual del encabezado en el panel de Citas
            self.texto_etiquetado.insert(
                tk.END, f'>>>({etiqueta})<<<\n', "negrita")
            self.texto_etiquetado.tag_configure(
                "negrita", font=("Arial", 12, "bold"))

            # Se aplica el subrayado al texto seleccionado
            tag_name = self.aplicar_subrayado(color_subrayado)

            # Gestión de Tooltips
            if etiqueta in self.tooltips_asignados:
                tooltip = self.tooltips_asignados[etiqueta]
            else:
                tooltip = Tooltip(self.texto_original, etiqueta)
                self.tooltips_asignados[etiqueta] = tooltip

            # Vinculación de eventos al tag creado
            self.texto_original.tag_bind(tag_name, "<Enter>", lambda event, tooltip=tooltip,
                                         tag_name=tag_name: tooltip.show_tooltip(event, tag_name))
            self.texto_original.tag_bind(
                tag_name, "<Leave>", tooltip.hide_tooltip)
            self.texto_original.tag_bind(
                tag_name, "<Motion>", tooltip.update_position)

            # Registro de la asignación
            self.etiquetas_asignadas.append((etiqueta, tag_name))

            self.guardar_subrayados()

            # Búsqueda de palabras clave para análisis automático (opcional)
            palabras_clave = self.palabras_clave_var.get().split(',')
            try:
                inicio_seleccion = self.texto_original.index(tk.SEL_FIRST)
                fin_seleccion = self.texto_original.index(tk.SEL_LAST)
                seleccion = self.texto_original.get(inicio_seleccion, fin_seleccion)
            except tk.TclError:
                seleccion = ""

            nuevos_parrafos_etiquetados = self.buscar_y_etiquetar_parrafos(
                palabras_clave, etiqueta, [seleccion])

            self.indices_etiquetados.extend(
                parrafo[0] for parrafo in nuevos_parrafos_etiquetados)
            self.parrafos_etiquetados.extend(nuevos_parrafos_etiquetados)
            
            # Actualización visual de paneles
            self.mostrar_fragmento_etiquetado(
                color_subrayado, nuevos_parrafos_etiquetados)
            self.actualizar_lista_etiquetado()
            self.guardar_etiquetado(nuevos_parrafos_etiquetados)
            return tag_name

    # --- MÉTODO PARA SELECCIONAR COLOR ---
    def elegir_color_subrayado(self):
        color_subrayado = colorchooser.askcolor()[1]
        if color_subrayado:
            return color_subrayado
        
    # --- MÉTODO PARA MOSTRAR FRAGMENTOS EN EL PANEL DERECHO ---
    def mostrar_fragmento_etiquetado(self, color_subrayado, nuevos_parrafos_etiquetados):
        for i, sentencia, etiqueta in nuevos_parrafos_etiquetados:

            # Se ajusta la anchura del fragmento mostrado
            wrapped_sentence = textwrap.fill(sentencia, width=40)

            # Siempre usamos un salto simple aquí porque el encabezado ya fue insertado
            # en la función 'etiquetar_fragmento' con la separación correcta.
            separador = "\n"

            # Se construye el texto final
            texto_etiquetado = f"{separador}{wrapped_sentence}\n"

            # ----------------------------------------------------------------------
            # SECCIÓN: INSERCIÓN DEL FRAGMENTO EN EL PANEL DERECHO
            # ----------------------------------------------------------------------
            self.texto_etiquetado.insert(tk.END, texto_etiquetado)

            # Auto-desplazamiento al final para mantener visible lo agregado
            self.texto_etiquetado.see(tk.END)

            # ----------------------------------------------------------------------
            # SECCIÓN: RE-APLICACIÓN VISUAL DEL SUBRAYADO EN EL TEXTO ORIGINAL
            # ----------------------------------------------------------------------
            tag_name_visual = f"Color_{color_subrayado}_{etiqueta.replace(' ', '_')}"
            try:
                inicio = self.texto_original.index(tk.SEL_FIRST)
                fin = self.texto_original.index(tk.SEL_LAST)

                self.texto_original.tag_add(tag_name_visual, inicio, fin)
                self.texto_original.tag_configure(
                    tag_name_visual,
                    underline=True,
                    font=("Arial", 13, "bold"),
                    foreground=color_subrayado
                )
            except tk.TclError:
                # En caso de no haber selección válida no se ejecuta nada
                pass

        # Asegura que el resaltado de selección siga siendo visible
        self.texto_original.tag_raise("sel")

    # --- MÉTODO PARA ELIMINAR SUBRAYADO SELECCIONADO ---
    def quitar_subrayado(self):
        try:
            try:
                sel_first = self.texto_original.index(tk.SEL_FIRST)
                sel_last = self.texto_original.index(tk.SEL_LAST)
                texto_seleccionado = self.texto_original.get(sel_first, sel_last)
            except tk.TclError:
                return

            tags_en_seleccion = self.texto_original.tag_names(sel_first)
            
            # Identificación de tags de color
            tags_a_eliminar = [tag for tag in tags_en_seleccion if tag.startswith("Color_")]

            if not tags_a_eliminar:
                return

            for tag in tags_a_eliminar:
                self.texto_original.tag_remove(tag, sel_first, sel_last)
                try:
                    self.texto_original.tag_unbind(tag, "<Enter>")
                    self.texto_original.tag_unbind(tag, "<Leave>")
                    self.texto_original.tag_unbind(tag, "<Motion>")
                except:
                    pass

                etiqueta_nombre = None
                
                # Eliminación de la lista de asignaciones
                copia_asignadas = list(self.etiquetas_asignadas)
                for item in copia_asignadas:
                    if item[1] == tag: 
                        etiqueta_nombre = item[0]
                        self.etiquetas_asignadas.remove(item)
                        break
                
                if not etiqueta_nombre:
                    partes = tag.split("_")
                    if len(partes) >= 3:
                        pass 

                # Limpieza de párrafos etiquetados en memoria
                if etiqueta_nombre:
                    texto_sel_clean = texto_seleccionado.strip().replace('\n', ' ')
                    
                    for i, (idx_sent, sentencia, etiq) in enumerate(self.parrafos_etiquetados):
                        if etiq == etiqueta_nombre:
                            sentencia_clean = sentencia.strip().replace('\n', ' ')
                            coincide = (texto_sel_clean in sentencia_clean) or \
                                       (sentencia_clean in texto_sel_clean) or \
                                       (len(texto_sel_clean) > 0 and texto_sel_clean == sentencia_clean)
                            if coincide:
                                del self.parrafos_etiquetados[i]
                                break

            self.guardar_subrayados()
            self.actualizar_lista_etiquetado()

        except Exception as e:
            print(f"Error al remover: {e}")

    # --- MÉTODO DE BÚSQUEDA Y ETIQUETADO AUTOMÁTICO ---
    def buscar_y_etiquetar_parrafos(self, palabras_clave, etiqueta, sentencias):
        parrafos_etiquetados = []
        for i, sentencia in enumerate(sentencias):
            if not palabras_clave or (len(palabras_clave)==1 and palabras_clave[0]==''):
                parrafos_etiquetados.append((i, sentencia, etiqueta))
            elif any(palabra.lower() in sentencia.lower() for palabra in palabras_clave):
                parrafos_etiquetados.append((i, sentencia, etiqueta))
        return parrafos_etiquetados

    # --- MÉTODO PARA RENDERIZAR EL CONTENIDO EN EL ÁREA PRINCIPAL ---
    def mostrar_contenido_original(self):
        if not self.tokens or not isinstance(self.tokens, (list, tuple)):
            self.tokens = []
        contenido_mostrar = '\n'.join(str(t) for t in self.tokens)
        self.texto_original.delete(1.0, tk.END)
        
        bold_font = font.Font(self.texto_original, self.texto_original.cget("font"))
        bold_font.configure(weight="bold")

        lineas = contenido_mostrar.split('\n')
        for i, linea in enumerate(lineas, start=1):
            self.texto_original.insert(tk.END, f"{i}\u2043 ", ("bold",))
            self.texto_original.insert(tk.END, f"{linea}\n\n")

        self.texto_original.tag_configure("bold", font=bold_font)

    # --- MÉTODO PARA NAVEGAR ENTRE ETIQUETAS (RESALTAR AL CLIC EN LISTA) ---
    def resaltar_etiqueta(self, tag_name):
        try:
            self.guardar_subrayados()
            
            etiqueta_buscada = None
            for etiq, tag in self.etiquetas_asignadas:
                if tag == tag_name:
                    etiqueta_buscada = etiq
                    break
            
            if not etiqueta_buscada:
                partes = tag_name.split('_')
                if len(partes) > 2:
                    pass

            if not etiqueta_buscada:
                return

            coincidencias_globales = []
            # Búsqueda en todos los archivos abiertos
            for nombre_archivo, datos in self.archivos_abiertos.items():
                if isinstance(datos, dict):
                    subrayados = datos.get("subrayados", [])
                    for sub in subrayados:
                        if sub["etiqueta"] == etiqueta_buscada:
                            start_idx = str(sub["start"])
                            try:
                                line, col = map(int, start_idx.split('.'))
                                sort_key = (nombre_archivo, line, col)
                            except ValueError:
                                sort_key = (nombre_archivo, 0, 0)

                            coincidencias_globales.append({
                                "archivo": nombre_archivo,
                                "start": sub["start"],
                                "end": sub["end"],
                                "color": sub["color"],
                                "tag": sub["tag"],
                                "sort_key": sort_key
                            })

            if not coincidencias_globales:
                messagebox.showinfo("Sin coincidencias", f"No hay fragmentos marcados como '{etiqueta_buscada}'.")
                return

            coincidencias_globales.sort(key=lambda x: x["sort_key"])

            if etiqueta_buscada not in self.indice_navegacion:
                self.indice_navegacion[etiqueta_buscada] = -1
            
            # Lógica de carrusel (siguiente coincidencia)
            self.indice_navegacion[etiqueta_buscada] += 1
            if self.indice_navegacion[etiqueta_buscada] >= len(coincidencias_globales):
                self.indice_navegacion[etiqueta_buscada] = 0
            
            match = coincidencias_globales[self.indice_navegacion[etiqueta_buscada]]

            nombre_actual = os.path.basename(self.ruta) if self.ruta else ""
            if match["archivo"] != nombre_actual:
                self.cambiar_archivo(match["archivo"])
                self.raiz.update_idletasks() 
            
            # Scroll y enfoque visual
            self.texto_original.see(match["start"])
            self.texto_original.tag_remove("resaltado", "1.0", tk.END)
            self.texto_original.tag_add("resaltado", match["start"], match["end"])
            self.texto_original.tag_config("resaltado", background="yellow")
            self.texto_original.focus_set()
            self.raiz.after(1000, lambda: self.texto_original.tag_remove("resaltado", "1.0", tk.END))

        except Exception as e:
            pass

    # --- MÉTODO PARA RECUPERAR TEXTO CODIFICADO AL PANEL DERECHO ---
    def recuperar_fragmento_codificado(self, tag_name):
        etiqueta_resaltada = None
        for etiqueta, tag in self.etiquetas_asignadas:
            if tag == tag_name:
                etiqueta_resaltada = etiqueta
                break

        if etiqueta_resaltada:
            fragmentos_por_etiqueta = {}
            for indice, sentencia, etiqueta in self.parrafos_etiquetados:
                if etiqueta == etiqueta_resaltada:
                    if etiqueta_resaltada not in fragmentos_por_etiqueta:
                        fragmentos_por_etiqueta[etiqueta_resaltada] = []
                    fragmentos_por_etiqueta[etiqueta_resaltada].append(
                        sentencia)

            # Verificar si ya existe contenido en el widget
            contenido_previo = self.texto_etiquetado.get("1.0", tk.END).strip()
            
            # --- MODIFICACIÓN PUNTO 1 (Excepción de primer fragmento y lógica estricta) ---
            if not contenido_previo:
                 # CASO 1: Si el panel estaba vacío -> 1 salto
                 self.texto_etiquetado.insert(tk.END, "\n")
            else:
                 # CASO 3: Si ya había contenido -> 2 saltos (requerido)
                 self.texto_etiquetado.insert(tk.END, "\n\n")

            for etiqueta, fragmentos in fragmentos_por_etiqueta.items():
                # Encabezado del código
                self.texto_etiquetado.insert(
                    tk.END, f">>>({etiqueta})<<<\n", "negrita")
                
                # Separación exclusiva de un renglón entre el nombre del código y el fragmento
                self.texto_etiquetado.insert(tk.END, "\n")

                for fragmento in fragmentos:
                    # Inserción del fragmento con espaciado balanceado (ni muy junto ni muy separado)
                    self.texto_etiquetado.insert(tk.END, fragmento + "\n\n")
            
            self.texto_etiquetado.tag_configure(
                "negrita", font=("Arial", 12, "bold"))
            
            # Se mueve la vista al final automáticamente tras insertar
            self.texto_etiquetado.see(tk.END)

    def restaurar_subrayado(self, tag_name):
        pass 
    
    # --- MÉTODO PARA GESTIONAR BARRA HORIZONTAL DINÁMICA ---
    def actualizar_scroll_horizontal_codigos(self):
        try:
            # Ancho visible del widget Text
            visible_w = self.lista_etiquetado.winfo_width()
            
            # Buscamos el ancho máximo entre los widgets hijos (botones de código)
            max_child_w = 0
            for child in self.lista_etiquetado.winfo_children():
                try:
                    # reqwidth nos dice cuánto espacio REAL necesita el botón
                    w = child.winfo_reqwidth()
                    if w > max_child_w:
                        max_child_w = w
                except:
                    pass

            # Lógica de visualización: Si el contenido es más ancho que el visor, mostrar barra
            # Se añade un pequeño margen (ej. 5px) para evitar parpadeos
            if max_child_w > (visible_w - 5):
                self.scrollHorizontal.grid()   # Mostrar
            else:
                self.scrollHorizontal.grid_remove()  # Ocultar

        except Exception:
            pass

    # --- MÉTODO PARA ACTUALIZAR LA LISTA DE CÓDIGOS (PANEL IZQUIERDO) ---
    def actualizar_lista_etiquetado(self):
        self.lista_etiquetado.config(state="normal") # Habilitar temporalmente para editar
        self.lista_etiquetado.delete(1.0, tk.END)
        
        # Limpieza de widgets previos
        for widget in self.lista_etiquetado.winfo_children():
            widget.destroy()

        etiquetas_unicas = set()

        # Espaciado inicial
        self.lista_etiquetado.insert(tk.END, "\n")

        for idx, (etiqueta, tag_name) in enumerate(self.etiquetas_asignadas, start=0):
            if etiqueta in etiquetas_unicas:
               continue
            etiquetas_unicas.add(etiqueta)

            # Cálculo del contador
            contador = sum(
                1 for _, _, etiq in self.parrafos_etiquetados if etiq == etiqueta)

            # Recuperación del color
            color_bg = None
            try:
                color_bg = self.texto_original.tag_cget(tag_name, "foreground")
            except Exception: pass

            if not color_bg:
                 try:
                     parts = tag_name.split('_')
                     if len(parts) > 1 and parts[1].startswith('#'):
                         color_bg = parts[1]
                 except Exception: pass
            
            if not color_bg:
                for datos in self.archivos_abiertos.values():
                    found = False
                    for sub in datos.get("subrayados", []):
                        if sub["tag"] == tag_name:
                            color_bg = sub["color"]
                            found = True
                            break
                    if found: break
            
            if not color_bg: color_bg = "gray"

            # --- CONSTRUCCIÓN DE LA FILA USANDO window_create ---
            
            # 1. Etiqueta de Conteo
            label_contador = tk.Label(self.lista_etiquetado, text=f"[{contador}]", font=(
                "Arial", 12, "bold"), fg="purple", bg="#FFFFCC")
            self.lista_etiquetado.window_create(tk.END, window=label_contador)
            
            # Espaciador
            self.lista_etiquetado.insert(tk.END, "  ")

            # 2. Botón de Color
            btn_color = tk.Button(self.lista_etiquetado, text="  ", bg=color_bg, relief="groove", borderwidth=2, command=lambda t=tag_name: self.resaltar_etiqueta(t))
            btn_color.bind("<Enter>", lambda event, btn=btn_color: btn.config(cursor="hand2"))
            btn_color.bind("<Leave>", lambda event, btn=btn_color: btn.config(cursor=""))
            self.lista_etiquetado.window_create(tk.END, window=btn_color)

            # Espaciador
            self.lista_etiquetado.insert(tk.END, "  ")

            # 3. Botón con el Nombre del Código
            btn_resaltar = tk.Button(self.lista_etiquetado, text=f"{etiqueta}", command=lambda t=tag_name: self.recuperar_fragmento_codificado(
                t), justify=tk.LEFT, font=("arial", 10, "bold"), bg="SystemButtonFace")
            
            # Hover effects
            btn_resaltar.bind("<Enter>", lambda event, btn=btn_resaltar: btn.config(cursor="hand2", bg="cyan"))
            btn_resaltar.bind("<Leave>", lambda event, btn=btn_resaltar: btn.config(cursor="", bg="SystemButtonFace"))

            # Menú contextual
            menu_contextual = tk.Menu(btn_resaltar, tearoff=0)
            menu_contextual.add_command(label="Eliminar Código", image=self.icono_eliminar, compound='left', font=(
                "arial", 11, "bold"), foreground="red", command=lambda lc=label_contador, bc=btn_color, br=btn_resaltar, e=etiqueta:
                self.eliminar_etiqueta(lc, bc, br, e))
            menu_contextual.add_separator()
            menu_contextual.add_command(
                label="Anexar a otro Código", image=self.icono_anexar, compound='left', font=(
                "arial", 12, "bold"), foreground="navy blue", command=lambda b=btn_resaltar, e=etiqueta: self.asignar_etiqueta(b, e))

            btn_resaltar.bind("<Button-3>", lambda event, menu=menu_contextual: menu.post(event.x_root, event.y_root))

            # Inserción del botón principal
            self.lista_etiquetado.window_create(tk.END, window=btn_resaltar)

            # Salto de línea para el siguiente elemento
            self.lista_etiquetado.insert(tk.END, "\n\n")

        # Verificación final de la barra de scroll
        self.actualizar_scroll_horizontal_codigos()

    # --- MÉTODO PARA ELIMINAR UNA ETIQUETA ---
    def eliminar_etiqueta(self, label_contador, boton_color, boton_resaltar, etiqueta):
        # Confirmación de seguridad
        confirmacion = messagebox.askyesno("Confirmar Eliminación", 
            f"¿Estás seguro de que deseas eliminar el código '{etiqueta}'?\n\nEsta acción eliminará todas las referencias y subrayados asociados.")
        if not confirmacion:
            return

        try:
            # En la versión mejorada, no necesitamos destruir los widgets manualmente uno por uno
            # ya que vamos a llamar a actualizar_lista_etiquetado() al final,
            # pero mantendremos la lógica de datos.

            # Eliminación en todos los archivos cargados
            for nombre_archivo, datos in self.archivos_abiertos.items():
                if isinstance(datos, dict):
                    subrayados = datos.get("subrayados", [])
                    nuevos_subrayados = []
                    for sub in subrayados:
                        if sub["etiqueta"] == etiqueta:
                            try:
                                self.texto_original.tag_remove(sub["tag"], "1.0", tk.END)
                                self.texto_original.tag_unbind(sub["tag"], "<Enter>")
                                self.texto_original.tag_unbind(sub["tag"], "<Leave>")
                                self.texto_original.tag_unbind(sub["tag"], "<Motion>")
                            except Exception:
                                pass
                        else:
                            nuevos_subrayados.append(sub)
                    datos["subrayados"] = nuevos_subrayados

            tags_a_borrar = []
            for tag in self.texto_original.tag_names():
                if etiqueta in tag or tag in [t for e, t in self.etiquetas_asignadas if e == etiqueta]:
                    tags_a_borrar.append(tag)
            
            for tag in tags_a_borrar:
                self.texto_original.tag_remove(tag, "1.0", tk.END)

            self.tooltips_asignados.pop(etiqueta, None)
            
            for color, etiq in list(self.color_tooltips.items()):
                if etiq == etiqueta:
                    self.color_tooltips.pop(color, None)

            self.etiquetas_asignadas = [et for et in self.etiquetas_asignadas if et[0] != etiqueta]
            self.parrafos_etiquetados = [p for p in self.parrafos_etiquetados if p[2] != etiqueta]

            self.raiz.update_idletasks()
            # La llamada crucial para limpiar la interfaz y que desaparezca la barra si es necesario
            self.actualizar_lista_etiquetado()
            self.guardar_subrayados() 

        except Exception as e:
            print(f"[Error al eliminar etiqueta: {e}]")

    # --- MÉTODO PARA FUSIONAR ETIQUETAS ---
    def asignar_etiqueta(self, boton, etiqueta_actual):
        nuevo_nombre = simpledialog.askstring(
            "Anexar", f"Nombre del código a Anexar:")
        if nuevo_nombre:
            if nuevo_nombre in [et[0] for et in self.etiquetas_asignadas]:
                self.combinar_etiquetas(etiqueta_actual, nuevo_nombre)
                self.actualizar_lista_etiquetado()

    # --- LÓGICA DE FUSIÓN DE ETIQUETAS ---
    def combinar_etiquetas(self, etiqueta_origen, etiqueta_destino):
        # 1. Obtener todos los tags afectados (del origen)
        tags_afectados = [tag for etiq, tag in self.etiquetas_asignadas if etiq == etiqueta_origen]

        # 2. Obtener o crear tooltip destino
        if etiqueta_destino in self.tooltips_asignados:
            tooltip_dest = self.tooltips_asignados[etiqueta_destino]
        else:
            tooltip_dest = Tooltip(self.texto_original, etiqueta_destino)
            self.tooltips_asignados[etiqueta_destino] = tooltip_dest

        # 3. Determinar el color destino (muy robusto)
        color_destino = None

        # Intento 1: Tomar color desde un tag activo en pantalla
        for etiq, tag in self.etiquetas_asignadas:
            if etiq == etiqueta_destino:
                try:
                    c = self.texto_original.tag_cget(tag, "foreground")
                    if c:
                        color_destino = c
                        break
                except:
                    pass

        # Intento 2: Tomar el color desde la estructura Color_#HEX_uuid
        if not color_destino:
            for etiq, tag in self.etiquetas_asignadas:
                if etiq == etiqueta_destino:
                    parts = tag.split("_")
                    if len(parts) >= 2 and parts[1].startswith("#"):
                        color_destino = parts[1]
                        break

        # Intento 3: Tomar de color_tooltips (respaldo)
        if not color_destino:
            for col, name in self.color_tooltips.items():
                if name == etiqueta_destino:
                    color_destino = col
                    break

        # Si por alguna razón no hay color aún, usar gris
        if not color_destino:
            color_destino = "#444444"

        # 4. ACTUALIZAR TODAS LAS ETIQUETAS VISUALES DEL ORIGEN
        for tag in tags_afectados:
            # Re-asignar tooltip
            self.texto_original.tag_bind(tag, "<Enter>", 
                lambda event, t=tooltip_dest, tg=tag: t.show_tooltip(event, tg))
            self.texto_original.tag_bind(tag, "<Leave>", tooltip_dest.hide_tooltip)
            self.texto_original.tag_bind(tag, "<Motion>", tooltip_dest.update_position)

            # *** PARTE CRUCIAL ***
            # Reconfigurar color y estilo del tag en pantalla
            try:
                self.texto_original.tag_configure(
                    tag,
                    underline=True,
                    font=("Arial", 13, "bold"),
                    foreground=color_destino
                )
            except:
                pass

        # 5. Actualizar estructuras lógicas
        fragmentos_origen = [
            p for p in self.parrafos_etiquetados if p[2] == etiqueta_origen
        ]

        # mover los fragmentos al destino
        self.parrafos_etiquetados.extend(
            [(i, s, etiqueta_destino) for i, s, _ in fragmentos_origen]
        )

        # actualizar etiquetas asignadas
        self.etiquetas_asignadas = [
            (etiqueta_destino if e == etiqueta_origen else e, t)
            for e, t in self.etiquetas_asignadas
        ]

        # limpiar origen
        self.parrafos_etiquetados = [
            p for p in self.parrafos_etiquetados if p[2] != etiqueta_origen
        ]

        # refrescar vista
        self.texto_original.update_idletasks()
        self.actualizar_lista_etiquetado()
        self.guardar_subrayados()

    # --- MÉTODO PARA CREAR SUBRAYADO VISUAL ---
    def aplicar_subrayado(self, color_subrayado):
        sel_first = self.texto_original.index(tk.SEL_FIRST)
        sel_last = self.texto_original.index(tk.SEL_LAST)

        identificador_unico = str(uuid.uuid4())[:8] 
        tag_name = f"Color_{color_subrayado}_{identificador_unico}"
        
        self.texto_original.tag_configure(tag_name, underline=True, font=(
            "Arial", 13, "bold"), foreground=color_subrayado)

        self.texto_original.tag_add(tag_name, sel_first, sel_last)
        
        self.texto_original.tag_raise("sel")
        
        return tag_name

    # --- MÉTODO PARA LIMPIAR EL PANEL DE CITAS ---
    def limpiar_contenido(self):
        self.texto_etiquetado.delete(1.0, tk.END)
        messagebox.showinfo("Removido", "Las citas del código se han removido.")

    # --- MÉTODO PARA PERSISTENCIA DE SUBRAYADOS ---
    def guardar_subrayados(self):
        if self.ruta:
            nombre_archivo = os.path.basename(self.ruta)
            subrayados = []

            tags_procesados = set()

            for etiqueta, tag_name in self.etiquetas_asignadas:
                ranges = self.texto_original.tag_ranges(tag_name)
                
                if ranges and tag_name not in tags_procesados:
                    start, end = ranges[0], ranges[1]
                    
                    try:
                        color = self.texto_original.tag_cget(tag_name, "foreground")
                    except:
                        # Fallback por si tag_cget falla (p.ej. si el tag no está en el widget actual)
                        color = "black"
                        parts = tag_name.split('_')
                        if len(parts) > 1 and parts[1].startswith('#'):
                            color = parts[1]

                    subrayados.append({
                        "tag": tag_name,
                        "start": start,
                        "end": end,
                        "color": color,
                        "etiqueta": etiqueta
                    })
                    tags_procesados.add(tag_name)

            self.archivos_abiertos[nombre_archivo] = {
                "contenido": self.contenido,
                "subrayados": subrayados
            }

    def restaurar_subrayados(self):
        pass

    # --- MÉTODO PARA EXPORTAR SOLO FRAGMENTOS ---
    def guardar_etiquetado(self, nuevos_parrafos_etiquetados):
        ruta_guardado = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Archivos de Texto", "*.txt")])

        if ruta_guardado:
            with open(ruta_guardado, 'w', encoding='utf-8') as archivo_guardado:
                contenido_guardar = ''
                for _, sentencia, etiqueta in nuevos_parrafos_etiquetados:
                    contenido_guardar += f">>>({self.etiqueta_actual})<<<\n\n{textwrap.fill(sentencia, width=40)}\n\n"
                archivo_guardado.write(contenido_guardar)
            messagebox.showinfo("Guardado", "El fragmento codificado se ha guardado correctamente.")

    # --- MÉTODO PARA EXPORTAR CITAS VISIBLES ---
    def guardar_codificado(self):
        contenido_editado = self.texto_etiquetado.get(1.0, tk.END)
        ruta_guardado = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Archivos de Texto", "*.txt")])

        self.guardar_subrayados()

        if ruta_guardado:
            with open(ruta_guardado, 'w', encoding='utf-8') as archivo_guardado:
                archivo_guardado.write(contenido_editado)
            messagebox.showinfo("Guardado", "El fragmento codificado se ha guardado correctamente.")

    # --- MÉTODO DE SALIDA Y CIERRE ---
    def salir_programa(self):
        self.guardar_subrayados() 
        
        # Limpieza de archivos inválidos antes de guardar
        archivos_validos = {}
        nombres_validos = set()

        for nombre, datos in self.archivos_abiertos.items():
            if datos.get("subrayados"): 
                archivos_validos[nombre] = datos
                nombres_validos.add(nombre)
        
        self.archivos_abiertos = archivos_validos
        
        self.historial_archivos = [
            h for h in self.historial_archivos 
            if h["nombre"] in nombres_validos
        ]
        
        # Estructura de datos para serialización (Pickle)
        datos_a_guardar = {
            "historial_archivos": list(self.historial_archivos),
            "etiquetas_asignadas": [(str(e), str(t)) for e, t in self.etiquetas_asignadas],
            "parrafos_etiquetados": [tuple(map(str, p)) for p in self.parrafos_etiquetados],
            "color_tooltips": dict(self.color_tooltips),
            "indice_navegacion": dict(self.indice_navegacion),
            "archivos_abiertos": {}
        }

        for nombre_archivo, datos in self.archivos_abiertos.items():
            contenido = datos.get("contenido", "")
            subrayados_guardados = []
            for sub in datos.get("subrayados", []):
                subrayados_guardados.append({
                    "tag": str(sub["tag"]),
                    "color": str(sub["color"]),
                    "start": str(sub["start"]),
                    "end": str(sub["end"]),
                    "etiqueta": str(sub["etiqueta"]) if sub["etiqueta"] else None
                })
            datos_a_guardar["archivos_abiertos"][nombre_archivo] = {
                "contenido": str(contenido),
                "subrayados": subrayados_guardados
            }

        # Guardado en disco
        with open("datos_codificacion.pkl", "wb") as archivo:
            pickle.dump(datos_a_guardar, archivo)

        # Destrucción de la ventana raíz
        self.raiz.destroy()

# --- BLOQUE PRINCIPAL DE EJECUCIÓN ---
if __name__ == "__main__":
    raiz = tk.Tk()
    raiz.geometry("1500x700")  
    app = EtiquetadoApp(raiz)
    raiz.mainloop()