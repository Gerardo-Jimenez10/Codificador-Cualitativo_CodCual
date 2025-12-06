import tkinter as tk
from tkinter import filedialog, messagebox, Menu, colorchooser, simpledialog
from tkinter import font
from tkinter import PhotoImage
from PIL import Image, ImageTk
import textwrap
import pickle
import docx
import fitz  # Se importa PyMuPDF para manejo de archivos PDF
import os
import uuid  # Se importa uuid para generar identificadores únicos

# --- IMPORTACIÓN Y MANEJO DE NLTK (PROCESAMIENTO DE LENGUAJE NATURAL) ---
import nltk
try:
    # Se intenta descargar el recurso 'punkt_tab' necesario para tokenización de manera silenciosa
    nltk.download('punkt_tab', quiet=True)
    # Se intenta descargar el recurso 'punkt' necesario para tokenización de manera silenciosa
    nltk.download('punkt', quiet=True)
except Exception:
    # Se captura cualquier excepción si falla la descarga y se continúa la ejecución sin interrupciones
    pass 

# --- HABILITAR ALTA RESOLUCIÓN (DPI AWARENESS) PARA SISTEMAS WINDOWS ---
try:
    from ctypes import windll
    # Se configura el proceso para reconocer la escala de DPI del monitor y evitar borrosidad en la interfaz gráfica
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    # Se ignora la excepción si el sistema operativo no es Windows o no soporta esta configuración específica
    pass

# --- FUNCIÓN GLOBAL PARA CARGAR CONTENIDO DE ARCHIVOS ---
def cargar_contenido(ruta_archivo):
    # Se verifica si la extensión del archivo corresponde a un archivo de texto plano (.txt)
    if ruta_archivo.lower().endswith('.txt'):
        # Se abre el archivo en modo lectura utilizando la codificación UTF-8
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            # Se lee todo el contenido del archivo y se almacena en la variable 'contenido'
            contenido = archivo.read()
    # Se verifica si la extensión del archivo corresponde a un documento de Word (.docx)
    elif ruta_archivo.lower().endswith('.docx'):
        # Se utiliza la librería docx para crear un objeto Document con el archivo especificado
        doc = docx.Document(ruta_archivo)
        # Se unen los textos de todos los párrafos del documento separándolos con saltos de línea
        contenido = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
    # Se verifica si la extensión del archivo corresponde a un documento PDF (.pdf)
    elif ruta_archivo.lower().endswith('.pdf'):
        # Se utiliza la librería fitz (PyMuPDF) para abrir el documento PDF
        pdf_doc = fitz.open(ruta_archivo)
        # Se inicializa la variable 'contenido' como una cadena de texto vacía
        contenido = ''
        # Se itera a través del rango de páginas del documento PDF
        for page_num in range(pdf_doc.page_count):
            # Se obtiene la página actual mediante su índice
            page = pdf_doc[page_num]
            # Se extrae el texto de la página actual y se concatena a la variable 'contenido'
            contenido += page.get_text()
    else:
        # Se lanza una excepción de tipo ValueError si el formato del archivo no es compatible
        raise ValueError(
            "Formato de archivo no compatible. Utilice archivos .txt, .docx o .pdf.")
    # Se retorna el contenido extraído del archivo procesado
    return contenido


# --- CLASE PARA LA CREACIÓN DE TOOLTIPS (VENTANAS EMERGENTES) ---
class Tooltip:
    def __init__(self, widget, text):
        # Se asigna el widget padre (donde aparecerá el tooltip) al atributo de instancia 'self.widget'
        self.widget = widget
        # Se asigna el texto que mostrará el tooltip al atributo de instancia 'self.text'
        self.text = text
        # Se inicializa la variable 'self.tooltip_window' como None para controlar su estado
        self.tooltip_window = None

    def show_tooltip(self, event, tag_name):
        # Se obtienen las coordenadas X e Y de la raíz del evento y se les suma un desplazamiento de 10 píxeles
        x, y = event.x_root + 10, event.y_root + 10

        # Se crea una nueva ventana Toplevel asociada al widget padre
        self.tooltip_window = tk.Toplevel(self.widget)
        # Se elimina la barra de título y los bordes de la ventana del tooltip para que parezca una etiqueta flotante
        self.tooltip_window.wm_overrideredirect(True)
        # Se establece la geometría de la ventana en la posición calculada previamente
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        # Se crea una etiqueta (Label) dentro de la ventana del tooltip con el formato deseado
        label = tk.Label(
            self.tooltip_window,
            text=str(self.text),         # Se establece el texto de la etiqueta
            justify='left',              # Se justifica el texto a la izquierda
            background='#FFFF66',        # Se establece el color de fondo amarillo claro
            relief='solid',              # Se establece un borde sólido alrededor de la etiqueta
            borderwidth=1,               # Se define el ancho del borde
            font=("arial", 11, "bold", "italic") # Se configura la fuente con estilo negrita y cursiva
        )
        # Se empaqueta la etiqueta dentro de la ventana con un relleno interno
        label.pack(ipadx=5, ipady=2)

        # Se cambia el cursor del widget padre a 'circle' para indicar visualmente la interacción
        self.widget.config(cursor="circle")

    def hide_tooltip(self, _):
        # Se comprueba si la ventana del tooltip existe actualmente
        if self.tooltip_window:
            # Se destruye la ventana del tooltip para ocultarla de la vista
            self.tooltip_window.destroy()
            # Se restablece la referencia de la ventana a None
            self.tooltip_window = None

        # Se restablece el cursor del widget padre a su estado por defecto
        self.widget.config(cursor="")

    def update_position(self, event):
        # Se comprueba si la ventana del tooltip está visible
        if self.tooltip_window:
            # Se calcula la nueva posición X sumando 10 píxeles a la posición actual del ratón
            x = event.x_root + 10
            # Se calcula la nueva posición Y sumando 10 píxeles a la posición actual del ratón
            y = event.y_root + 10
            # Se actualiza la geometría de la ventana del tooltip con las nuevas coordenadas dinámicas
            self.tooltip_window.geometry(f"+{x}+{y}")

# --- FUNCIÓN AUXILIAR PARA RUTAS RELATIVAS (COMPATIBILIDAD CON PYINSTALLER) ---
def ruta_relativa(ruta):
    import sys, os
    # Se verifica si el atributo '_MEIPASS' existe en el módulo sys (indicativo de ejecución en entorno empaquetado PyInstaller)
    if hasattr(sys, "_MEIPASS"):
        # Se construye la ruta absoluta uniendo el directorio temporal de PyInstaller con la ruta relativa dada
        return os.path.join(sys._MEIPASS, ruta)
    # Se retorna la ruta original sin cambios si no se está ejecutando desde un empaquetado
    return ruta

# --- CLASE PRINCIPAL DE LA APLICACIÓN ---
class EtiquetadoApp:
    def __init__(self, raiz):
        # Se llama al constructor de la clase padre para inicializar
        super().__init__()
        # Se asigna la ventana raíz de Tkinter al atributo 'self.raiz'
        self.raiz = raiz
        # Se establece el título de la ventana principal de la aplicación
        self.raiz.title('"Codificador Cualitativo"')
        # Se configura el color de fondo de la ventana principal a verde
        self.raiz.configure(bg="green")
        # Se establece el estado de la ventana a maximizado ("zoomed") para ocupar toda la pantalla
        self.raiz.state("zoomed")
        # Se define el tamaño mínimo de la ventana para asegurar la visibilidad correcta de los elementos
        self.raiz.minsize(800, 600)

        # --- VARIABLES DE CONTROL TKINTER ---
        # Se inicializa la variable de control tipo cadena para las palabras clave
        self.palabras_clave_var = tk.StringVar()
        # Se inicializa la variable de control tipo cadena para la etiqueta actual
        self.etiqueta_var = tk.StringVar()

        # --- ESTRUCTURAS DE DATOS ---
        # Se inicializa un diccionario para almacenar los archivos abiertos y sus datos asociados
        self.archivos_abiertos = {}
        # Se inicializa un diccionario para mapear nombres de etiquetas con sus objetos Tooltip correspondientes
        self.tooltips_asignados = {}
        # Se inicializa una lista para mantener el historial de rutas de archivos accedidos
        self.historial_archivos = []
        # Se inicializa un diccionario para almacenar los colores asociados a los tooltips/etiquetas
        self.color_tooltips = {}
        # Se inicializa un diccionario para gestionar el índice de navegación de búsqueda entre etiquetas
        self.indice_navegacion = {} 

        # Se inicializan las variables de estado para la ruta y contenido del archivo actual como nulas
        self.ruta = None
        self.contenido = None

        # --- CONFIGURACIÓN DEL MENÚ PRINCIPAL ---
        # Se crea el objeto de menú principal
        self.barraMenu = Menu(self.raiz)
        # Se configura la ventana raíz para utilizar esta barra de menú
        self.raiz.configure(menu=self.barraMenu)

        # --- CARGA DE ÍCONOS Y RECURSOS GRÁFICOS ---
        # Se obtiene el directorio base absoluto donde se encuentra el script actual
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Se resuelve la ruta base relativa compatible con el empaquetado (si aplica)
        ruta_base = ruta_relativa(base_dir)
        # Se construye la ruta completa al archivo de imagen del logo
        icono_ruta = os.path.join(ruta_base, "Logo.png")

        # Se intenta cargar y establecer el ícono de la ventana principal
        try:
            imagen_icono = Image.open(icono_ruta)
            self.icono_tk = ImageTk.PhotoImage(imagen_icono)
            self.raiz.iconphoto(True, self.icono_tk)
        except Exception:
            # Se captura y se ignora el error si no se puede cargar el ícono (fallback silencioso)
            pass 

        # Se construye la ruta al directorio que contiene los íconos de la interfaz
        ruta_iconos = ruta_relativa(os.path.join(base_dir, "Iconos"))

        # Se define una función local para cargar imágenes de íconos manejando excepciones de forma segura
        def cargar_icono(nombre):
            try:
                # Se intenta crear y retornar un objeto PhotoImage con la ruta del archivo especificado
                return PhotoImage(file=os.path.join(ruta_iconos, nombre))
            except Exception:
                # Se retorna None si falla la carga del ícono
                return None

        # Se cargan los íconos específicos para cada acción del menú utilizando la función local
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
        # Se crea el menú desplegable 'Archivo' sin la línea punteada de separación (tearoff=0)
        self.menu_desplegable = Menu(self.barraMenu, tearoff=0)
        # Se añade la opción 'Importar Archivo' al menú con su comando, imagen y estilo asociados
        self.menu_desplegable.add_command(label="Importar Archivo", image=self.icono_importar, compound='left', font=(
            "arial", 12, "bold"), foreground="red", command=self.importar_archivo)
        # Se añade un separador visual en el menú
        self.menu_desplegable.add_separator()
        # Se añade la opción 'Guardar Codificado' al menú
        self.menu_desplegable.add_command(label="Guardar Codificado", image=self.icono_guardado, compound='left', font=(
            "arial", 12, "bold"), foreground="brown", command=self.guardar_codificado)
        # Se añade otro separador visual
        self.menu_desplegable.add_separator()
        # Se añade la opción 'Salir' al menú
        self.menu_desplegable.add_command(label="Salir", image=self.icono_salir, compound='left', font=(
            "arial", 12, "bold"), foreground="Green", command=self.salir_programa)

        # --- SUBMENÚ EDICIÓN ---
        # Se crea el menú desplegable 'Edición'
        self.edicionMenu = Menu(self.barraMenu, tearoff=0)
        # Se añade la opción 'Limpiar Citas del Código' al menú de edición
        self.edicionMenu.add_command(label="Limpiar Citas del Código", image=self.icono_limpiar, compound='left', font=(
            "arial", 12, "bold"), foreground="navy blue", command=self.limpiar_contenido)

        # --- SUBMENÚ INFORMACIÓN ---
        # Se crea el menú desplegable 'Información'
        self.menu_información = Menu(self.barraMenu, tearoff=0)
        # Se añade la opción 'Acerca de...' para mostrar los créditos
        self.menu_información.add_command(
            label="Acerca de...", compound='left', image=self.icono_info, font=(
                "arial", 12, "bold"), foreground="purple", command=self.mostrar_informacion)

        # --- SUBMENÚ HISTORIAL ---
        # Se crea el menú desplegable 'Historial' para listar los archivos abiertos recientemente
        self.menu_archivos_abiertos = Menu(self.barraMenu, tearoff=0)

        # Se añaden los menús creados a la barra de menú principal en cascada
        self.barraMenu.add_cascade(label="Archivo", menu=self.menu_desplegable)
        self.barraMenu.add_cascade(label="Edición", menu=self.edicionMenu)
        self.barraMenu.add_cascade(label="Historial", menu=self.menu_archivos_abiertos)
        self.barraMenu.add_cascade(label="Información", menu=self.menu_información)

        # Se crea una etiqueta para el título central de la aplicación y se coloca en la grilla
        tk.Label(raiz, text="CodCual", font=("Magneto", 32, "bold"),
                 fg="yellow", bg="green").grid(row=0, column=2, padx=(20, 20), pady=(8, 40))


        # =========================================================================================
        # SECCIÓN DE CONTROL DE TAMAÑOS Y DISTRIBUCIÓN DE PANELES (FRAMES DE LA INTERFAZ)
        # =========================================================================================
        
        # -------------------- ÁREA 1: PANEL IZQUIERDO (LISTA DE CÓDIGOS) --------------------
        
        # Se crea y posiciona la etiqueta de encabezado para la lista de codificaciones
        tk.Label(raiz, text="Lista de Codificaciones Realizadas", font=("arial", 12, "bold"), bg="cyan").grid(
            row=4, column=0, columnspan=2, padx=(8, 0), pady=(8, 0), sticky='ew')

        # --- FRAME CONTENEDOR PARA MANEJAR SCROLL HORIZONTAL Y VERTICAL ---
        # Se crea un Frame contenedor para albergar la lista y sus barras de desplazamiento
        frame_lista = tk.Frame(raiz)
        # Se posiciona el frame contenedor en la grilla principal
        frame_lista.grid(row=5, column=0, pady=(0, 8), padx=(8, 0), sticky='nsew')
        
        # Se configura el peso de la fila y columna del frame contenedor para que se expanda dinámicamente
        frame_lista.grid_rowconfigure(0, weight=1)
        frame_lista.grid_columnconfigure(0, weight=1)

        # Widget de Texto (Lista): 
        # Se crea el widget de texto sin ajuste de línea automático (wrap="none") para listar los códigos
        self.lista_etiquetado = tk.Text(
            frame_lista, wrap="none", width=30, height=24, bg="#FFFFCC")
        # Se posiciona el widget de texto dentro del frame contenedor
        self.lista_etiquetado.grid(row=0, column=0, sticky='nsew')
        
        # Se bloquean los eventos de teclado y ratón para evitar la edición manual en la lista de códigos
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
        # Se crea la barra de desplazamiento vertical y se asocia al widget de texto de la lista
        scrollVertical3 = tk.Scrollbar(
            frame_lista, command=self.lista_etiquetado.yview)
        # Se posiciona la barra vertical en el frame
        scrollVertical3.grid(row=0, column=1, sticky="ns")
        # Se configura el widget de texto para usar esta barra vertical
        self.lista_etiquetado.config(yscrollcommand=scrollVertical3.set)

        # --- Barra de desplazamiento HORIZONTAL (Dinámica) ---
        # Se crea la barra de desplazamiento horizontal y se asocia al widget de texto
        self.scrollHorizontal = tk.Scrollbar(
            frame_lista, orient="horizontal", command=self.lista_etiquetado.xview)
        
        # Se coloca inicialmente en la grilla (su visibilidad se gestionará dinámicamente por evento)
        self.scrollHorizontal.grid(row=1, column=0, sticky="ew")
        # Se configura el widget de texto para usar esta barra horizontal
        self.lista_etiquetado.config(xscrollcommand=self.scrollHorizontal.set)
        
        # Se vincula el evento de configuración para actualizar la visibilidad del scroll horizontal según necesidad
        self.lista_etiquetado.bind("<Configure>", lambda e: self.actualizar_scroll_horizontal_codigos())


        # -------------------- ÁREA 2: PANEL CENTRAL (TEXTO ORIGINAL) --------------------
        
        # Se crea la etiqueta de encabezado para el área de texto central
        tk.Label(raiz, text="Texto", font=("arial", 12, "bold"), bg="#99FF00").grid(
            row=4, column=2, columnspan=2, pady=(8, 0), padx=(8, 0), sticky='ew')

        # Widget de Texto (Central)
        # Se crea el widget de texto principal con ajuste por palabra (wrap=tk.WORD) para mostrar el contenido
        self.texto_original = tk.Text(raiz, wrap=tk.WORD, width=77, height=23, font=(
            "Arial", 13))   
        # Se posiciona el widget de texto central en la grilla
        self.texto_original.grid(row=5, column=2, padx=(
            8, 0), pady=(0, 8), sticky='nsew')

        # Barra de desplazamiento para el texto original
        # Se crea y posiciona la barra vertical para el texto central
        scrollVertical1 = tk.Scrollbar(raiz, command=self.texto_original.yview)
        scrollVertical1.grid(row=5, column=3, pady=(0, 8), sticky="nsew")
        # Se conecta la barra al widget de texto central
        self.texto_original.config(yscrollcommand=scrollVertical1.set)


        # -------------------- ÁREA 3: PANEL DERECHO (CITAS DEL CÓDIGO) --------------------
        
        # Se crea la etiqueta de encabezado para el panel de citas extraídas
        tk.Label(raiz, text="Citas del Código", font=("arial", 12, "bold"), bg="#FF93F2").grid(
            row=4, column=4, columnspan=2, pady=(8, 0), padx=(8, 8), sticky='ew')

        # Widget de Texto (Derecho)
        # Se crea el widget de texto para mostrar las citas extraídas y formateadas
        self.texto_etiquetado = tk.Text(
            raiz, wrap=tk.WORD, width=30, height=23, font=("Arial", 13))
        # Se posiciona el widget en la grilla
        self.texto_etiquetado.grid(row=5, column=4, padx=(
            8, 0), pady=(0, 8), sticky='nsew')
        # Se establece el color de fondo específico para este widget
        self.texto_etiquetado.configure(bg="#FFFFCC")

        # Barra de desplazamiento para las citas
        # Se crea y posiciona la barra vertical para el panel de citas
        scrollVertical2 = tk.Scrollbar(
            raiz, command=self.texto_etiquetado.yview)
        scrollVertical2.grid(row=5, column=5, pady=(0, 8),
                             padx=(0, 8), sticky="nsew")
        # Se conecta la barra al widget de citas
        self.texto_etiquetado.config(yscrollcommand=scrollVertical2.set)


        # -------------------- CONTROL DE EXPANSIÓN (WEIGHTS) --------------------
        
        # Se configura el peso de la fila 5 para permitir expansión vertical
        raiz.grid_rowconfigure(5, weight=1)
        # Se configuran los pesos de las columnas para distribuir el espacio horizontalmente de forma proporcional
        raiz.grid_columnconfigure(0, weight=1)     # Panel Izquierdo
        raiz.grid_columnconfigure(2, weight=1)     # Panel Central
        raiz.grid_columnconfigure(4, weight=1)     # Panel Derecho

        # =========================================================================================

        # --- INICIALIZACIÓN DE VARIABLES DE ESTADO ---
        # Se inicializan las variables de estado en None o listas vacías según corresponda
        self.ruta = None
        self.contenido = None
        self.tokens = None
        self.sentencias = None
        self.etiqueta_actual = None
        self.parrafos_etiquetados = []
        self.indices_etiquetados = []
        self.etiquetas_asignadas = []

        # Se llama al método para actualizar la lista visual de etiquetas (inicialmente vacía)
        self.actualizar_lista_etiquetado()

        # --- RECUPERACIÓN DE DATOS GUARDADOS (PERSISTENCIA) ---
        datos_guardados = {}
        try:
            # Se intenta abrir el archivo pickle para leer datos de sesiones previas
            with open("datos_codificacion.pkl", "rb") as archivo_datos:
                datos_guardados = pickle.load(archivo_datos)
        except (FileNotFoundError, Exception):
            # Si hay error o no existe el archivo, se inicia con un diccionario vacío
            datos_guardados = {}

        # Se cargan los datos recuperados en las variables de instancia correspondientes
        self.historial_archivos = datos_guardados.get("historial_archivos", [])
        self.archivos_abiertos = datos_guardados.get("archivos_abiertos", {})
        self.etiquetas_asignadas = datos_guardados.get("etiquetas_asignadas", [])
        self.parrafos_etiquetados = datos_guardados.get("parrafos_etiquetados", [])
        self.color_tooltips = datos_guardados.get("color_tooltips", {})
        self.indice_navegacion = datos_guardados.get("indice_navegacion", {})

        # Validación y recuperación de tokens
        self.tokens = datos_guardados.get("tokens", [])
        # Se asegura que 'self.tokens' sea una lista válida
        if not isinstance(self.tokens, list):
            self.tokens = list(self.tokens) if self.tokens else []

        # Validación y recuperación de sentencias
        self.sentencias = datos_guardados.get("sentencias", [])
        # Se asegura que 'self.sentencias' sea una lista válida
        if not isinstance(self.sentencias, list):
            self.sentencias = list(self.sentencias) if self.sentencias else []

        # Se actualiza el menú de historial en la interfaz gráfica
        self.actualizar_menu_historial()

        # --- RESTAURACIÓN DE LA ÚLTIMA SESIÓN ---
        # Se verifica si hay archivos abiertos registrados previamente
        if self.archivos_abiertos:
            # Se obtiene el primer archivo y sus datos del diccionario
            nombre_archivo, datos = next(iter(self.archivos_abiertos.items()))
            self.contenido = datos.get("contenido", "")
            # Se intenta re-tokenizar el contenido para tener las estructuras de texto listas
            try:
                self.tokens = nltk.sent_tokenize(self.contenido)
                self.sentencias = nltk.sent_tokenize(self.contenido)
            except:
                 # Se aplica un método alternativo de separación si NLTK falla
                 self.tokens = self.contenido.split('.')
                 self.sentencias = self.contenido.split('.')

            # Se muestra el contenido en el panel central
            self.mostrar_contenido_original()
            
            # Se restaura la ruta completa del archivo buscando en el historial
            for h in self.historial_archivos:
                if h["nombre"] == nombre_archivo:
                    self.ruta = h["ruta"]
                    break

            # Se restauran visualmente los subrayados, estilos y tooltips guardados
            for sub in datos.get("subrayados", []):
                tag_name = sub["tag"]
                start, end = sub["start"], sub["end"]
                color = sub["color"]
                etiqueta = sub["etiqueta"]

                # Se recrea el tag en el widget de texto
                self.texto_original.tag_add(tag_name, start, end)
                # Se configura el estilo visual del tag recuperado
                self.texto_original.tag_configure(
                    tag_name, underline=True, font=("Arial", 13, "bold"), foreground=color
                )

                # Se recrea el objeto Tooltip asociado al fragmento
                tooltip = Tooltip(self.texto_original, etiqueta)
                # Se vinculan los eventos de ratón para mostrar/ocultar el tooltip restaurado
                self.texto_original.tag_bind(tag_name, "<Enter>", lambda e, t=tooltip, tg=tag_name: t.show_tooltip(e, tg))
                self.texto_original.tag_bind(tag_name, "<Leave>", tooltip.hide_tooltip)
                self.texto_original.tag_bind(tag_name, "<Motion>", tooltip.update_position)

            # Se asegura que la selección de texto esté visible por encima de otros tags
            self.texto_original.tag_raise("sel")
        
        # Se refresca la lista lateral de etiquetas con los datos cargados
        self.actualizar_lista_etiquetado()

        # --- EVENTOS DEL MOUSE ---
        # Se asocia el movimiento del ratón para cambiar el cursor dinámicamente sobre áreas etiquetadas
        self.texto_original.bind(
            "<Motion>", self.cambiar_cursor_segun_posicion)

        # --- MENÚ CONTEXTUAL (CLIC DERECHO) ---
        # Se crea el menú contextual para el texto original
        self.menu_contextual_texto_original = Menu(
            self.texto_original, tearoff=0)
        # Se añade la opción 'Codificar' al menú contextual
        self.menu_contextual_texto_original.add_command(label="Codificar", image=self.icono_codificar, compound='left', font=(
            "arial", 12, "bold"), foreground="purple", command=self.etiquetar_fragmento)
        # Se añade un separador visual
        self.menu_contextual_texto_original.add_separator()
        # Se añade la opción 'Remover Codificado' al menú contextual
        self.menu_contextual_texto_original.add_command(label="Remover Codificado", image=self.icono_remover, compound='left', font=(
            "arial", 12, "bold"), foreground="red", command=self.quitar_subrayado)
        # Se vincula el evento de clic derecho (Button-3) para mostrar el menú
        self.texto_original.bind(
            "<Button-3>", self.mostrar_menu_contextual_texto_original)

    # --- MÉTODO PARA MOSTRAR INFORMACIÓN DEL DESARROLLADOR ---
    def mostrar_informacion(self):
        # Se muestra una ventana de mensaje modal con la información de la aplicación y el autor
        messagebox.showinfo("Acerca de...",
                            "          Aplicación desarrollada en Python.\n\n"
                            "                  Derechos reservados®\n\n"
                            '         "GERARDO HERNÁNDEZ JIMÉNEZ"\n\n'
                            "   Egresado de la Licenciatura en Informática.\n\n"
                            "        Centro Universitario UAEM Texcoco.\n\n"
                            " Universidad Autónoma del Estado de México.")

    # --- MÉTODO PARA DESPLEGAR EL MENÚ CONTEXTUAL ---
    def mostrar_menu_contextual_texto_original(self, event):
        # Se despliega el menú contextual en las coordenadas actuales del evento del ratón
        self.menu_contextual_texto_original.post(event.x_root, event.y_root)

    # --- MÉTODO PARA REGISTRAR UN ARCHIVO EN EL SISTEMA INTERNO ---
    def agregar_archivo_abierto(self, nombre_archivo, contenido):
        # Se verifica si el archivo no existe ya en el diccionario de archivos abiertos
        if nombre_archivo not in self.archivos_abiertos:
            # Se añade el archivo con su contenido y una lista vacía de subrayados
            self.archivos_abiertos[nombre_archivo] = {
                "contenido": contenido,
                "subrayados": []
            }
            # Se añade la entrada al menú de historial de la barra de menú principal
            self.menu_archivos_abiertos.add_command(
                label=nombre_archivo,
                command=lambda nombre=nombre_archivo: self.cambiar_archivo(nombre)
            )

    # --- MÉTODO PARA CAMBIAR ENTRE ARCHIVOS CARGADOS ---
    def cambiar_archivo(self, nombre_archivo, guardar_antes=True):
        # 1. Se guardan los subrayados y cambios actuales antes de realizar el cambio de archivo
        # Se añade condición para evitar guardar si ya se manipularon los datos en memoria (caso específico de fusión)
        if guardar_antes:
            self.guardar_subrayados()

        # Se verifica si el archivo solicitado existe en el registro de archivos abiertos
        if nombre_archivo in self.archivos_abiertos:
            datos = self.archivos_abiertos[nombre_archivo]
            
            # Se busca la ruta completa correspondiente en el historial
            encontrado = False
            for h in self.historial_archivos:
                if h["nombre"] == nombre_archivo:
                    self.ruta = h["ruta"]
                    encontrado = True
                    break
            # Si no se encuentra en el historial, se obtiene la ruta absoluta del nombre de archivo
            if not encontrado:
                self.ruta = os.path.abspath(nombre_archivo) 

            # Se carga el contenido del nuevo archivo seleccionado
            self.contenido = datos.get("contenido", "")
            # Se intenta tokenizar el contenido nuevamente para preparar el texto
            try:
                self.tokens = nltk.sent_tokenize(self.contenido)
                self.sentencias = nltk.sent_tokenize(self.contenido)
            except:
                # Se usa tokenización simple basada en puntos si falla la librería NLTK
                self.tokens = self.contenido.split('.')
                self.sentencias = self.contenido.split('.')

            # Se muestra el contenido nuevo en el editor central
            self.mostrar_contenido_original()

            # Se restauran las etiquetas visuales y los tooltips asociados desde los datos guardados
            for subrayado in datos.get("subrayados", []):
                tag_name = subrayado['tag']
                start = subrayado['start']
                end = subrayado['end']
                color = subrayado['color']
                etiqueta = subrayado['etiqueta']

                # Se añade el tag al rango de texto especificado
                self.texto_original.tag_add(tag_name, start, end)
                # Se configura el estilo visual del tag (subrayado, color, fuente)
                self.texto_original.tag_configure(
                    tag_name, underline=True, font=("Arial", 13, "bold"), foreground=color
                )

                # Se crea y vincula el tooltip correspondiente a la etiqueta
                tooltip = Tooltip(self.texto_original, etiqueta)
                self.texto_original.tag_bind(tag_name, "<Enter>", lambda event, tooltip=tooltip, tag_name=tag_name: tooltip.show_tooltip(event, tag_name))
                self.texto_original.tag_bind(tag_name, "<Leave>", tooltip.hide_tooltip)
                self.texto_original.tag_bind(tag_name, "<Motion>", tooltip.update_position)

            # Se asegura que la selección de texto esté visible (capa superior)
            self.texto_original.tag_raise("sel")

    # --- MÉTODO PARA IMPORTAR NUEVOS ARCHIVOS ---
    def importar_archivo(self):
        # Se abre el diálogo del sistema operativo para seleccionar un archivo
        self.ruta = filedialog.askopenfilename(title="Importar Archivo", filetypes=[
                                               ("Todos los archivos", "*.*")])
        # Se procede únicamente si se seleccionó una ruta válida
        if self.ruta:
            # Se carga el contenido del archivo seleccionado usando la función global
            self.contenido = cargar_contenido(self.ruta)
            
            # Se realiza el proceso de tokenización del contenido
            try:
                self.tokens = nltk.sent_tokenize(self.contenido)
                self.sentencias = nltk.sent_tokenize(self.contenido)
            except (LookupError, Exception):
                # Fallback de tokenización manual si ocurre un error con NLTK
                self.tokens = self.contenido.replace('\n', ' ').split('.')
                self.sentencias = self.contenido.replace('\n', ' ').split('.')
                # Se asegura que los tokens conserven el punto final
                self.tokens = [t + '.' for t in self.tokens if t.strip()]
                self.sentencias = [s + '.' for s in self.sentencias if s.strip()]

            # Se renderiza el contenido procesado en la interfaz
            self.mostrar_contenido_original()
            
            # Se configura el estilo de alto contraste para la selección de texto
            self.texto_original.tag_configure("sel", background="#0078D7", foreground="white")
            self.texto_original.tag_raise("sel")

            # Se extrae el nombre base del archivo para su identificación
            nombre_archivo = os.path.basename(self.ruta)
            # Se registra el archivo en la estructura de datos interna
            self.agregar_archivo_abierto(nombre_archivo, self.contenido)

            # Se actualiza el historial de archivos, evitando duplicados en la lista
            registro = {"nombre": nombre_archivo, "ruta": self.ruta}
            self.historial_archivos = [
                r for r in self.historial_archivos if r["ruta"] != self.ruta
            ]
            self.historial_archivos.append(registro)

            # Se actualiza el menú visual del historial en la barra de menú
            self.actualizar_menu_historial()

    # --- MÉTODO PARA RESTAURAR CURSOR POR DEFECTO ---
    def restaurar_cursor(self, event):
        # Se restablece el cursor del widget que disparó el evento a su estado normal
        event.widget.config(cursor="")

    # --- MÉTODO PARA ACTUALIZAR EL MENÚ DE HISTORIAL ---
    def actualizar_menu_historial(self):
        # Se eliminan todas las entradas actuales del menú de historial
        self.menu_archivos_abiertos.delete(0, tk.END)

        # Se verifica si no hay archivos abiertos actualmente
        if not self.archivos_abiertos:
            # Se muestra una opción deshabilitada indicando "(Vacío)"
            self.menu_archivos_abiertos.add_command(
                label="(Vacío)",
                state="disabled",
                font=("Arial", 11)
            )
            return

        # Se itera sobre las claves (nombres) de los archivos abiertos
        for nombre in self.archivos_abiertos.keys():
            # Se añade cada archivo como un comando en el menú para permitir el cambio rápido
            self.menu_archivos_abiertos.add_command(
                label=nombre,
                font=("Arial", 11),
                command=lambda n=nombre: self.cambiar_archivo(n)
            )

    # --- MÉTODO PARA DETECTAR HOVER SOBRE ETIQUETAS ---
    def cambiar_cursor_segun_posicion(self, event):
        # Se obtienen las coordenadas X e Y del ratón en el evento
        x, y = event.x, event.y
        # Se comprueba qué tags (etiquetas de texto) existen en esa posición específica
        tags = self.texto_original.tag_names("@{},{}".format(x, y))
        # Si alguno de los tags encontrados comienza con "Color_", se cambia el cursor a un círculo
        if any(tag.startswith("Color_") for tag in tags):
            self.texto_original.config(cursor="circle")
        else:
            # De lo contrario, se usa el cursor de texto estándar (xterm)
            self.texto_original.config(cursor="xterm")

    # --- MÉTODO PRINCIPAL DE CODIFICACIÓN (ETIQUETADO) ---
    def etiquetar_fragmento(self):
        # Se solicita al usuario el nombre del código mediante un diálogo de entrada
        etiqueta = simpledialog.askstring("Codificar", "Escribe un Código:")
        if etiqueta:
            # Se abre el selector de color para que el usuario elija un color de resaltado
            color_subrayado = self.elegir_color_subrayado()

            # Si no se selecciona un color (cancelación), se aborta la operación
            if not color_subrayado:
                return 

            # Se actualiza la variable que almacena la etiqueta actual
            self.etiqueta_actual = etiqueta

            # -------------------------------------------------------------------------
            # LÓGICA DE ESPACIADO Y SEPARACIÓN ENTRE BLOQUES DE CÓDIGOS (AJUSTADO)
            # -------------------------------------------------------------------------
            
            # Se obtiene el contenido actual del panel de citas para determinar el espaciado necesario
            contenido_actual_texto = self.texto_etiquetado.get("1.0", tk.END).strip()
            
            if not contenido_actual_texto:
                 # CASO 1: Si la pantalla está vacía, se añade un solo salto de línea
                 self.texto_etiquetado.insert(tk.END, "\n")
            
            else:
                 # Se inicia el escaneo del contenido para identificar el último bloque insertado
                 ultimo_codigo_nombre = ""
                 content_raw = self.texto_etiquetado.get("1.0", tk.END)
                 
                 # Se divide el contenido por los marcadores de inicio de código estándar
                 bloques = content_raw.split(">>>(")
                 if len(bloques) > 1:
                     # Se toma el último bloque de texto
                     ultimo_bloque = bloques[-1]
                     # Se extrae el nombre de la etiqueta hasta el marcador de cierre
                     if ")<<<" in ultimo_bloque:
                         ultimo_codigo_nombre = ultimo_bloque.split(")<<<")[0]

                 # Se aplican las reglas de salto según si el código es el mismo o diferente al anterior
                 if ultimo_codigo_nombre == etiqueta:
                     # CASO 2: Mismo código -> Se inserta 1 salto de línea
                     self.texto_etiquetado.insert(tk.END, "\n")
                 else:
                     # CASO 3: Códigos distintos -> Se insertan 2 saltos de línea
                     self.texto_etiquetado.insert(tk.END, "\n\n")

            # -------------------------------------------------------------------------

            # Se inserta el encabezado del código con formato de negrita en el panel de citas
            self.texto_etiquetado.insert(
                tk.END, f'>>>({etiqueta})<<<\n', "negrita")
            # Se configura el tag "negrita" para aplicar el estilo visual correcto
            self.texto_etiquetado.tag_configure(
                "negrita", font=("Arial", 12, "bold"))

            # Se aplica el subrayado visual en el texto original y se obtiene el nombre único del tag generado
            tag_name = self.aplicar_subrayado(color_subrayado)

            # Se gestiona la creación o recuperación del objeto Tooltip
            if etiqueta in self.tooltips_asignados:
                tooltip = self.tooltips_asignados[etiqueta]
            else:
                tooltip = Tooltip(self.texto_original, etiqueta)
                self.tooltips_asignados[etiqueta] = tooltip

            # Se vinculan los eventos de ratón al nuevo tag para mostrar/ocultar el tooltip
            self.texto_original.tag_bind(tag_name, "<Enter>", lambda event, tooltip=tooltip,
                                         tag_name=tag_name: tooltip.show_tooltip(event, tag_name))
            self.texto_original.tag_bind(
                tag_name, "<Leave>", tooltip.hide_tooltip)
            self.texto_original.tag_bind(
                tag_name, "<Motion>", tooltip.update_position)

            # Se registra la asignación en la lista global de etiquetas asignadas
            self.etiquetas_asignadas.append((etiqueta, tag_name))

            # Se guarda el estado actual de los subrayados para persistencia
            self.guardar_subrayados()

            # Se obtienen las palabras clave para el análisis (si las hay) desde la variable de control
            palabras_clave = self.palabras_clave_var.get().split(',')
            try:
                # Se intenta obtener el texto actualmente seleccionado por el usuario
                inicio_seleccion = self.texto_original.index(tk.SEL_FIRST)
                fin_seleccion = self.texto_original.index(tk.SEL_LAST)
                seleccion = self.texto_original.get(inicio_seleccion, fin_seleccion)
            except tk.TclError:
                # Si no hay selección, se establece como cadena vacía
                seleccion = ""

            # Se buscan y etiquetan los párrafos correspondientes basados en la selección
            nuevos_parrafos_etiquetados = self.buscar_y_etiquetar_parrafos(
                palabras_clave, etiqueta, [seleccion])

            # Se actualizan las listas globales de índices y párrafos etiquetados
            self.indices_etiquetados.extend(
                parrafo[0] for parrafo in nuevos_parrafos_etiquetados)
            self.parrafos_etiquetados.extend(nuevos_parrafos_etiquetados)
            
            # Se actualizan los paneles visuales con los nuevos datos
            self.mostrar_fragmento_etiquetado(
                color_subrayado, nuevos_parrafos_etiquetados)
            self.actualizar_lista_etiquetado()
            # Se guarda el etiquetado en un archivo de texto externo (si aplica la lógica de autoguardado)
            self.guardar_etiquetado(nuevos_parrafos_etiquetados)
            # Se retorna el nombre del tag creado
            return tag_name

    # --- MÉTODO PARA SELECCIONAR COLOR ---
    def elegir_color_subrayado(self):
        # Se abre el selector de color y se obtiene el valor hexadecimal del color elegido
        color_subrayado = colorchooser.askcolor()[1]
        if color_subrayado:
            return color_subrayado
        
    # --- MÉTODO PARA MOSTRAR FRAGMENTOS EN EL PANEL DERECHO ---
    def mostrar_fragmento_etiquetado(self, color_subrayado, nuevos_parrafos_etiquetados):
        # Se itera sobre la lista de nuevos párrafos etiquetados
        for i, sentencia, etiqueta in nuevos_parrafos_etiquetados:

            # Se ajusta el ancho del texto de la sentencia para visualización
            wrapped_sentence = textwrap.fill(sentencia, width=40)

            # Se define el separador (el encabezado ya se gestionó previamente)
            separador = "\n"

            # Se construye la cadena final de texto a insertar
            texto_etiquetado = f"{separador}{wrapped_sentence}\n"

            # ----------------------------------------------------------------------
            # SECCIÓN: INSERCIÓN DEL FRAGMENTO EN EL PANEL DERECHO
            # ----------------------------------------------------------------------
            # Se inserta el texto formateado en el widget de citas
            self.texto_etiquetado.insert(tk.END, texto_etiquetado)

            # Se desplaza la vista del widget al final para mostrar lo agregado
            self.texto_etiquetado.see(tk.END)

            # ----------------------------------------------------------------------
            # SECCIÓN: RE-APLICACIÓN VISUAL DEL SUBRAYADO EN EL TEXTO ORIGINAL
            # ----------------------------------------------------------------------
            # Se genera el nombre del tag visual combinando color y nombre de etiqueta
            tag_name_visual = f"Color_{color_subrayado}_{etiqueta.replace(' ', '_')}"
            try:
                # Se obtienen los índices de la selección actual del usuario
                inicio = self.texto_original.index(tk.SEL_FIRST)
                fin = self.texto_original.index(tk.SEL_LAST)

                # Se aplica el tag y su configuración al texto original
                self.texto_original.tag_add(tag_name_visual, inicio, fin)
                self.texto_original.tag_configure(
                    tag_name_visual,
                    underline=True,
                    font=("Arial", 13, "bold"),
                    foreground=color_subrayado
                )
            except tk.TclError:
                # Se ignora la excepción si no hay selección válida en este momento
                pass

        # Se eleva la etiqueta "sel" para mantener visible la selección del usuario sobre el coloreado
        self.texto_original.tag_raise("sel")

    # --- MÉTODO PARA ELIMINAR SUBRAYADO SELECCIONADO ---
    def quitar_subrayado(self):
        try:
            try:
                # Se intenta obtener los índices y texto de la selección actual
                sel_first = self.texto_original.index(tk.SEL_FIRST)
                sel_last = self.texto_original.index(tk.SEL_LAST)
                texto_seleccionado = self.texto_original.get(sel_first, sel_last)
            except tk.TclError:
                # Se retorna inmediatamente si no hay selección
                return

            # Se obtienen todos los tags presentes en el inicio de la selección
            tags_en_seleccion = self.texto_original.tag_names(sel_first)
            
            # Se filtran los tags que corresponden a colores (creados por la aplicación)
            tags_a_eliminar = [tag for tag in tags_en_seleccion if tag.startswith("Color_")]

            # Si no hay tags para eliminar en la selección, se retorna
            if not tags_a_eliminar:
                return

            # Se itera sobre los tags identificados para eliminar
            for tag in tags_a_eliminar:
                # Se remueve el tag del rango de texto seleccionado
                self.texto_original.tag_remove(tag, sel_first, sel_last)
                try:
                    # Se desvinculan los eventos asociados al tag (hover, leave, motion)
                    self.texto_original.tag_unbind(tag, "<Enter>")
                    self.texto_original.tag_unbind(tag, "<Leave>")
                    self.texto_original.tag_unbind(tag, "<Motion>")
                except:
                    pass

                etiqueta_nombre = None
                
                # Se busca y elimina la referencia en la lista global de etiquetas asignadas
                copia_asignadas = list(self.etiquetas_asignadas)
                for item in copia_asignadas:
                    if item[1] == tag: 
                        etiqueta_nombre = item[0]
                        self.etiquetas_asignadas.remove(item)
                        break
                
                # Manejo de fallback para intentar obtener el nombre del tag si no se encontró
                if not etiqueta_nombre:
                    partes = tag.split("_")
                    if len(partes) >= 3:
                        pass 

                # Se limpian los párrafos etiquetados almacenados en memoria
                if etiqueta_nombre:
                    texto_sel_clean = texto_seleccionado.strip().replace('\n', ' ')
                    
                    for i, (idx_sent, sentencia, etiq) in enumerate(self.parrafos_etiquetados):
                        if etiq == etiqueta_nombre:
                            sentencia_clean = sentencia.strip().replace('\n', ' ')
                            # Se comprueba la coincidencia entre el texto seleccionado y el guardado
                            coincide = (texto_sel_clean in sentencia_clean) or \
                                       (sentencia_clean in texto_sel_clean) or \
                                       (len(texto_sel_clean) > 0 and texto_sel_clean == sentencia_clean)
                            if coincide:
                                del self.parrafos_etiquetados[i]
                                break

            # Se guardan los cambios realizados en los subrayados
            self.guardar_subrayados()
            # Se actualiza la lista visual de etiquetas en el panel izquierdo
            self.actualizar_lista_etiquetado()

        except Exception as e:
            # Se imprime el error en consola si ocurre alguna excepción durante el proceso
            print(f"Error al remover: {e}")

    # --- MÉTODO DE BÚSQUEDA Y ETIQUETADO AUTOMÁTICO ---
    def buscar_y_etiquetar_parrafos(self, palabras_clave, etiqueta, sentencias):
        parrafos_etiquetados = []
        # Se itera sobre las sentencias proporcionadas para analizar
        for i, sentencia in enumerate(sentencias):
            # Si no hay palabras clave definidas, se etiqueta todo el contenido
            if not palabras_clave or (len(palabras_clave)==1 and palabras_clave[0]==''):
                parrafos_etiquetados.append((i, sentencia, etiqueta))
            # Si hay coincidencia de alguna palabra clave en la sentencia, se etiqueta
            elif any(palabra.lower() in sentencia.lower() for palabra in palabras_clave):
                parrafos_etiquetados.append((i, sentencia, etiqueta))
        # Se retorna la lista de párrafos que fueron procesados y etiquetados
        return parrafos_etiquetados

    # --- MÉTODO PARA RENDERIZAR EL CONTENIDO EN EL ÁREA PRINCIPAL ---
    def mostrar_contenido_original(self):
        # Se valida que la variable tokens sea una lista válida
        if not self.tokens or not isinstance(self.tokens, (list, tuple)):
            self.tokens = []
        # Se une el contenido de los tokens para mostrarlo
        contenido_mostrar = '\n'.join(str(t) for t in self.tokens)
        # Se limpia el área de texto central completamente
        self.texto_original.delete(1.0, tk.END)
        
        # Se crea una fuente en negrita basada en la fuente actual del widget
        bold_font = font.Font(self.texto_original, self.texto_original.cget("font"))
        bold_font.configure(weight="bold")

        # Se divide el contenido por líneas e inserta con numeración visual
        lineas = contenido_mostrar.split('\n')
        for i, linea in enumerate(lineas, start=1):
            self.texto_original.insert(tk.END, f"{i}\u2043 ", ("bold",))
            self.texto_original.insert(tk.END, f"{linea}\n\n")

        # Se configura el tag para que la numeración aparezca en negrita
        self.texto_original.tag_configure("bold", font=bold_font)

    # --- MÉTODO PARA NAVEGAR ENTRE ETIQUETAS (RESALTAR AL CLIC EN LISTA) ---
    def resaltar_etiqueta(self, tag_name):
        try:
            # Se guardan los subrayados actuales antes de navegar
            self.guardar_subrayados()
            
            # Se busca el nombre de la etiqueta asociado al tag proporcionado
            etiqueta_buscada = None
            for etiq, tag in self.etiquetas_asignadas:
                if tag == tag_name:
                    etiqueta_buscada = etiq
                    break
            
            # Intento de recuperación por nombre del tag si falla la búsqueda directa
            if not etiqueta_buscada:
                partes = tag_name.split('_')
                if len(partes) > 2:
                    pass

            # Si no se encuentra etiqueta asociada, se retorna
            if not etiqueta_buscada:
                return

            coincidencias_globales = []
            # Se realiza la búsqueda de coincidencias en todos los archivos abiertos
            for nombre_archivo, datos in self.archivos_abiertos.items():
                if isinstance(datos, dict):
                    subrayados = datos.get("subrayados", [])
                    for sub in subrayados:
                        if sub["etiqueta"] == etiqueta_buscada:
                            # Se prepara la clave de ordenamiento basada en la posición
                            start_idx = str(sub["start"])
                            try:
                                line, col = map(int, start_idx.split('.'))
                                sort_key = (nombre_archivo, line, col)
                            except ValueError:
                                sort_key = (nombre_archivo, 0, 0)

                            # Se añade el hallazgo a la lista de coincidencias globales
                            coincidencias_globales.append({
                                "archivo": nombre_archivo,
                                "start": sub["start"],
                                "end": sub["end"],
                                "color": sub["color"],
                                "tag": sub["tag"],
                                "sort_key": sort_key
                            })

            # Si no hay coincidencias globales, se notifica al usuario
            if not coincidencias_globales:
                messagebox.showinfo("Sin coincidencias", f"No hay fragmentos marcados como '{etiqueta_buscada}'.")
                return

            # Se ordenan las coincidencias para una navegación secuencial lógica
            coincidencias_globales.sort(key=lambda x: x["sort_key"])

            # Se inicializa el índice de navegación para esa etiqueta si no existe
            if etiqueta_buscada not in self.indice_navegacion:
                self.indice_navegacion[etiqueta_buscada] = -1
            
            # Lógica de carrusel: Se avanza al siguiente índice en la lista
            self.indice_navegacion[etiqueta_buscada] += 1
            # Si se supera el límite de coincidencias, se vuelve al inicio (carrusel)
            if self.indice_navegacion[etiqueta_buscada] >= len(coincidencias_globales):
                self.indice_navegacion[etiqueta_buscada] = 0
            
            # Se obtiene la coincidencia actual según el índice
            match = coincidencias_globales[self.indice_navegacion[etiqueta_buscada]]

            # Se cambia de archivo si la coincidencia está en otro documento distinto al actual
            nombre_actual = os.path.basename(self.ruta) if self.ruta else ""
            if match["archivo"] != nombre_actual:
                self.cambiar_archivo(match["archivo"])
                self.raiz.update_idletasks() 
            
            # Se realiza scroll hasta la coincidencia y se aplica un resaltado temporal (amarillo)
            self.texto_original.see(match["start"])
            self.texto_original.tag_remove("resaltado", "1.0", tk.END)
            self.texto_original.tag_add("resaltado", match["start"], match["end"])
            self.texto_original.tag_config("resaltado", background="yellow")
            self.texto_original.focus_set()
            # Se programa la eliminación del resaltado temporal después de 1 segundo (1000 ms)
            self.raiz.after(1000, lambda: self.texto_original.tag_remove("resaltado", "1.0", tk.END))

        except Exception as e:
            # Se captura cualquier error durante la navegación para no bloquear la app
            pass

    # --- MÉTODO PARA RECUPERAR TEXTO CODIFICADO AL PANEL DERECHO ---
    def recuperar_fragmento_codificado(self, tag_name):
        # Se busca el nombre de la etiqueta correspondiente al tag
        etiqueta_resaltada = None
        for etiqueta, tag in self.etiquetas_asignadas:
            if tag == tag_name:
                etiqueta_resaltada = etiqueta
                break

        if etiqueta_resaltada:
            # Se agrupan los fragmentos existentes por su etiqueta
            fragmentos_por_etiqueta = {}
            for indice, sentencia, etiqueta in self.parrafos_etiquetados:
                if etiqueta == etiqueta_resaltada:
                    if etiqueta_resaltada not in fragmentos_por_etiqueta:
                        fragmentos_por_etiqueta[etiqueta_resaltada] = []
                    fragmentos_por_etiqueta[etiqueta_resaltada].append(
                        sentencia)

            # Se verifica si ya existe contenido en el widget de citas
            contenido_previo = self.texto_etiquetado.get("1.0", tk.END).strip()
            
            # --- MODIFICACIÓN PUNTO 1 (Excepción de primer fragmento y lógica estricta) ---
            if not contenido_previo:
                 # CASO 1: Si el panel estaba vacío -> Se inserta 1 salto
                 self.texto_etiquetado.insert(tk.END, "\n")
            else:
                 # CASO 3: Si ya había contenido -> Se insertan 2 saltos
                 self.texto_etiquetado.insert(tk.END, "\n\n")

            # Se itera para insertar los fragmentos recuperados en el panel
            for etiqueta, fragmentos in fragmentos_por_etiqueta.items():
                # Se inserta el encabezado del código
                self.texto_etiquetado.insert(
                    tk.END, f">>>({etiqueta})<<<\n", "negrita")
                
                # Se inserta una separación de un renglón
                self.texto_etiquetado.insert(tk.END, "\n")

                for fragmento in fragmentos:
                    # Se inserta el fragmento con espaciado adecuado
                    self.texto_etiquetado.insert(tk.END, fragmento + "\n\n")
            
            # Se configura la fuente del encabezado insertado
            self.texto_etiquetado.tag_configure(
                "negrita", font=("Arial", 12, "bold"))
            
            # Se mueve la vista al final automáticamente tras insertar
            self.texto_etiquetado.see(tk.END)

    def restaurar_subrayado(self, tag_name):
        # Función reservada para futura implementación de restauración específica
        pass 
    
    # --- MÉTODO PARA GESTIONAR BARRA HORIZONTAL DINÁMICA ---
    def actualizar_scroll_horizontal_codigos(self):
        try:
            # Se obtiene el ancho visible del widget Text de la lista
            visible_w = self.lista_etiquetado.winfo_width()
            
            # Se busca el ancho máximo requerido entre los widgets hijos (botones)
            max_child_w = 0
            for child in self.lista_etiquetado.winfo_children():
                try:
                    # Se obtiene el ancho requerido por el widget hijo actual
                    w = child.winfo_reqwidth()
                    if w > max_child_w:
                        max_child_w = w
                except:
                    pass

            # Lógica de visualización: Si el contenido es más ancho que el visor, se muestra la barra
            if max_child_w > (visible_w - 5):
                self.scrollHorizontal.grid()   # Se muestra la barra de scroll
            else:
                self.scrollHorizontal.grid_remove()  # Se oculta la barra de scroll

        except Exception:
            # Se ignoran errores durante el cálculo geométrico
            pass

    # --- MÉTODO PARA ACTUALIZAR LA LISTA DE CÓDIGOS (PANEL IZQUIERDO) ---
    def actualizar_lista_etiquetado(self):
        # Se habilita temporalmente el widget para permitir la edición y limpieza
        self.lista_etiquetado.config(state="normal") 
        # Se limpia todo el contenido actual del widget
        self.lista_etiquetado.delete(1.0, tk.END)
        
        # Se destruyen los widgets hijos previos (botones) para evitar duplicados
        for widget in self.lista_etiquetado.winfo_children():
            widget.destroy()

        etiquetas_unicas = set()

        # Se inserta un espaciado inicial en la lista
        self.lista_etiquetado.insert(tk.END, "\n")

        # Se itera sobre las etiquetas asignadas para renderizarlas
        for idx, (etiqueta, tag_name) in enumerate(self.etiquetas_asignadas, start=0):
            if etiqueta in etiquetas_unicas:
               continue
            etiquetas_unicas.add(etiqueta)

            # Se calcula cuántas veces aparece esta etiqueta en los párrafos
            contador = sum(
                1 for _, _, etiq in self.parrafos_etiquetados if etiq == etiqueta)

            # Se intenta recuperar el color de fondo asociado al tag
            color_bg = None
            try:
                # Intento obtener el color desde el tag en el texto original si existe
                color_bg = self.texto_original.tag_cget(tag_name, "foreground")
            except Exception: pass

            # Fallback para obtener el color desde el nombre del tag si no está presente en el texto original
            if not color_bg:
                 try:
                     parts = tag_name.split('_')
                     if len(parts) > 1 and parts[1].startswith('#'):
                         color_bg = parts[1]
                 except Exception: pass
            
            # Fallback buscando en archivos guardados globalmente si no se ha encontrado aún
            if not color_bg:
                for datos in self.archivos_abiertos.values():
                    found = False
                    for sub in datos.get("subrayados", []):
                        if sub["tag"] == tag_name:
                            color_bg = sub["color"]
                            found = True
                            break
                    if found: break
            
            # Se asigna un color por defecto (gris) si no se encuentra ninguno
            if not color_bg: color_bg = "gray"

            # --- CONSTRUCCIÓN DE LA FILA USANDO window_create ---
            
            # 1. Se crea e inserta la etiqueta de Conteo
            label_contador = tk.Label(self.lista_etiquetado, text=f"[{contador}]", font=(
                "Arial", 12, "bold"), fg="purple", bg="#FFFFCC")
            self.lista_etiquetado.window_create(tk.END, window=label_contador)
            
            # Se inserta un espaciador visual
            self.lista_etiquetado.insert(tk.END, "  ")

            # 2. Se crea e inserta el Botón de Color
            btn_color = tk.Button(self.lista_etiquetado, text="  ", bg=color_bg, relief="groove", borderwidth=2, command=lambda t=tag_name: self.resaltar_etiqueta(t))
            btn_color.bind("<Enter>", lambda event, btn=btn_color: btn.config(cursor="hand2"))
            btn_color.bind("<Leave>", lambda event, btn=btn_color: btn.config(cursor=""))
            self.lista_etiquetado.window_create(tk.END, window=btn_color)

            # Se inserta un espaciador visual
            self.lista_etiquetado.insert(tk.END, "  ")

            # 3. Se crea e inserta el Botón con el Nombre del Código (Etiqueta)
            btn_resaltar = tk.Button(self.lista_etiquetado, text=f"{etiqueta}", command=lambda t=tag_name: self.recuperar_fragmento_codificado(
                t), justify=tk.LEFT, font=("arial", 10, "bold"), bg="SystemButtonFace")
            
            # Se configuran los efectos de Hover (pasar el ratón por encima)
            btn_resaltar.bind("<Enter>", lambda event, btn=btn_resaltar: btn.config(cursor="hand2", bg="cyan"))
            btn_resaltar.bind("<Leave>", lambda event, btn=btn_resaltar: btn.config(cursor="", bg="SystemButtonFace"))

            # Se crea y configura el menú contextual específico para el botón
            menu_contextual = tk.Menu(btn_resaltar, tearoff=0)
            menu_contextual.add_command(label="Eliminar Código", image=self.icono_eliminar, compound='left', font=(
                "arial", 11, "bold"), foreground="red", command=lambda lc=label_contador, bc=btn_color, br=btn_resaltar, e=etiqueta:
                self.eliminar_etiqueta(lc, bc, br, e))
            menu_contextual.add_separator()
            menu_contextual.add_command(
                label="Anexar a otro Código", image=self.icono_anexar, compound='left', font=(
                "arial", 12, "bold"), foreground="navy blue", command=lambda b=btn_resaltar, e=etiqueta: self.asignar_etiqueta(b, e))

            # Se vincula el menú contextual al evento de clic derecho
            btn_resaltar.bind("<Button-3>", lambda event, menu=menu_contextual: menu.post(event.x_root, event.y_root))

            # Se inserta el botón principal en la ventana de texto
            self.lista_etiquetado.window_create(tk.END, window=btn_resaltar)

            # Se inserta salto de línea para separar el siguiente elemento
            self.lista_etiquetado.insert(tk.END, "\n\n")

        # Se verifica finalmente el estado de la barra de scroll horizontal
        self.actualizar_scroll_horizontal_codigos()

    # --- MÉTODO PARA ELIMINAR UNA ETIQUETA ---
    def eliminar_etiqueta(self, label_contador, boton_color, boton_resaltar, etiqueta):
        # Se solicita confirmación de seguridad al usuario antes de eliminar
        confirmacion = messagebox.askyesno("Confirmar Eliminación", 
            f"¿Estás seguro de que deseas eliminar el código '{etiqueta}'?\n\nEsta acción eliminará todas las referencias y subrayados asociados al código asignado en la interfaz.")
        if not confirmacion:
            return

        try:
            # Se procede a la eliminación en todos los archivos cargados
            for nombre_archivo, datos in self.archivos_abiertos.items():
                if isinstance(datos, dict):
                    subrayados = datos.get("subrayados", [])
                    nuevos_subrayados = []
                    # Se filtran los subrayados para eliminar los de la etiqueta seleccionada
                    for sub in subrayados:
                        if sub["etiqueta"] == etiqueta:
                            try:
                                # Se remueve visualmente el tag y se desvinculan sus eventos
                                self.texto_original.tag_remove(sub["tag"], "1.0", tk.END)
                                self.texto_original.tag_unbind(sub["tag"], "<Enter>")
                                self.texto_original.tag_unbind(sub["tag"], "<Leave>")
                                self.texto_original.tag_unbind(sub["tag"], "<Motion>")
                            except Exception:
                                pass
                        else:
                            nuevos_subrayados.append(sub)
                    # Se actualiza la lista de subrayados en los datos del archivo
                    datos["subrayados"] = nuevos_subrayados

            # Se identifican y limpian tags residuales en el widget de texto actual
            tags_a_borrar = []
            for tag in self.texto_original.tag_names():
                if etiqueta in tag or tag in [t for e, t in self.etiquetas_asignadas if e == etiqueta]:
                    tags_a_borrar.append(tag)
            
            for tag in tags_a_borrar:
                self.texto_original.tag_remove(tag, "1.0", tk.END)

            # Se eliminan las referencias de los tooltips y colores en los diccionarios
            self.tooltips_asignados.pop(etiqueta, None)
            
            for color, etiq in list(self.color_tooltips.items()):
                if etiq == etiqueta:
                    self.color_tooltips.pop(color, None)

            # Se eliminan las asignaciones y párrafos correspondientes de la memoria
            self.etiquetas_asignadas = [et for et in self.etiquetas_asignadas if et[0] != etiqueta]
            self.parrafos_etiquetados = [p for p in self.parrafos_etiquetados if p[2] != etiqueta]

            # Se actualizan las tareas pendientes de la interfaz gráfica
            self.raiz.update_idletasks()
            # Se llama a actualizar la lista visual para reflejar los cambios realizados
            self.actualizar_lista_etiquetado()
            # Se guardan los cambios persistentemente
            self.guardar_subrayados() 

        except Exception as e:
            # Se imprime el error en consola en caso de fallo durante la eliminación
            print(f"[Error al eliminar etiqueta: {e}]")

    # --- MÉTODO PARA FUSIONAR ETIQUETAS ---
    def asignar_etiqueta(self, boton, etiqueta_actual):
        # Se solicita el nombre del código destino para la fusión mediante un diálogo
        nuevo_nombre = simpledialog.askstring(
            "Anexar", f"Nombre del código a Anexar:")
        if nuevo_nombre:
            # Si el nombre existe en las etiquetas asignadas, se procede a combinar
            if nuevo_nombre in [et[0] for et in self.etiquetas_asignadas]:
                self.combinar_etiquetas(etiqueta_actual, nuevo_nombre)
                self.actualizar_lista_etiquetado()

    # --- LÓGICA DE FUSIÓN DE ETIQUETAS (ACTUALIZACIÓN GLOBAL AUTOMÁTICA) ---
    def combinar_etiquetas(self, etiqueta_origen, etiqueta_destino):
        """
        Fusiona 'etiqueta_origen' en 'etiqueta_destino'.
        Actualiza los datos de subrayado en TODOS los archivos (visibles u ocultos),
        unifica colores y tooltips, y refresca la vista actual automáticamente.
        """
        
        # 1. Asegurar el estado actual antes de proceder
        # Esto guarda los cambios visuales del documento actual en self.archivos_abiertos
        self.guardar_subrayados()

        # 2. Determinar el color de destino (usando lógica existente)
        color_destino = None
        
        # Intento A: Buscar color en asignaciones existentes
        for etiq, tag in self.etiquetas_asignadas:
            if etiq == etiqueta_destino:
                parts = tag.split("_")
                if len(parts) >= 2 and parts[1].startswith("#"):
                    color_destino = parts[1]
                    break
        
        # Intento B: Buscar en caché de colores
        if not color_destino:
            for col, name in self.color_tooltips.items():
                if name == etiqueta_destino:
                    color_destino = col
                    break

        # Intento C: Color por defecto si no se encuentra otro
        if not color_destino:
            color_destino = "#444444"

        # 3. ACTUALIZACIÓN MASIVA EN ESTRUCTURA DE DATOS (ARCHIVOS ABIERTOS)
        # Se recorren TODOS los archivos cargados, no solo el visible.
        
        for nombre_archivo, datos in self.archivos_abiertos.items():
            subrayados = datos.get("subrayados", [])
            nuevos_subrayados_archivo = []
            
            for sub in subrayados:
                if sub["etiqueta"] == etiqueta_origen:
                    # Si el subrayado pertenece a la etiqueta origen, se actualiza
                    
                    # Se genera un nuevo tag único que incluya el nuevo color
                    # Esto es crucial para que al cargar el archivo, se aplique el estilo correcto
                    nuevo_tag_id = str(uuid.uuid4())[:8]
                    nuevo_tag_nombre = f"Color_{color_destino}_{nuevo_tag_id}"
                    
                    # Se actualiza el registro con los nuevos datos
                    sub["etiqueta"] = etiqueta_destino
                    sub["color"] = color_destino
                    sub["tag"] = nuevo_tag_nombre
                
                nuevos_subrayados_archivo.append(sub)
            
            # Se guarda la lista actualizada en el archivo correspondiente
            datos["subrayados"] = nuevos_subrayados_archivo

        # 4. ACTUALIZACIÓN DE METADATOS GLOBALES
        
        # Actualizar lista de párrafos etiquetados (para exportación y recuperación)
        # Se crea una nueva lista donde se reemplaza el nombre de la etiqueta antigua por la nueva
        self.parrafos_etiquetados = [
            (idx, txt, etiqueta_destino if etiq == etiqueta_origen else etiq)
            for idx, txt, etiq in self.parrafos_etiquetados
        ]

        # Reconstruir la lista de etiquetas asignadas globalmente
        # Se escanea 'archivos_abiertos' para tener la lista maestra actualizada
        # esto asegura que los botones del panel izquierdo tengan los TAGS nuevos correctos
        nueva_lista_asignadas = []
        for nombre_archivo, datos in self.archivos_abiertos.items():
            for sub in datos.get("subrayados", []):
                # Se añade el par (NombreEtiqueta, NombreTag)
                nueva_lista_asignadas.append((sub["etiqueta"], sub["tag"]))
        
        self.etiquetas_asignadas = nueva_lista_asignadas

        # Actualizar caché de tooltips (si existe la ventana, se actualiza referencia)
        if etiqueta_destino not in self.tooltips_asignados:
             self.tooltips_asignados[etiqueta_destino] = Tooltip(self.texto_original, etiqueta_destino)

        # 5. REFRESCO VISUAL AUTOMÁTICO
        # Para que el usuario vea los cambios INMEDIATAMENTE sin hacer nada,
        # se recarga el archivo actual usando la función cambiar_archivo.
        # Como ya se actualizó 'self.archivos_abiertos' (la fuente de verdad),
        # al recargar, se pintarán los subrayados con los nuevos colores y tooltips.
        
        nombre_actual = ""
        if self.ruta:
            nombre_actual = os.path.basename(self.ruta)
            # Se encuentra el nombre exacto en el diccionario por seguridad
            for k in self.archivos_abiertos.keys():
                if self.archivos_abiertos[k]["contenido"] == self.contenido: 
                    if k == nombre_actual:
                         break
                    
        # --- 8) Mensaje de confirmación ---
            messagebox.showinfo(
                "Anexación completada",
                f"El contenido del código '{etiqueta_origen}' ha sido anexado correctamente a '{etiqueta_destino}'."
            )
            
            # Se fuerza la recarga del archivo actual para redibujar la interfaz.
            # IMPORTANTE: Se usa guardar_antes=False porque la vista actual tiene TAGS VIEJOS.
            # Si se guarda ahora, el sistema buscará los tags nuevos (que ya están en memoria) en la vista vieja,
            # no los encontrará, y guardará una lista vacía, borrando los subrayados.
            self.cambiar_archivo(nombre_actual, guardar_antes=False)

    # --- MÉTODO PARA CREAR SUBRAYADO VISUAL ---
    def aplicar_subrayado(self, color_subrayado):
        # Se obtienen los índices de inicio y fin de la selección actual
        sel_first = self.texto_original.index(tk.SEL_FIRST)
        sel_last = self.texto_original.index(tk.SEL_LAST)

        # Se genera un identificador único para el tag visual
        identificador_unico = str(uuid.uuid4())[:8] 
        tag_name = f"Color_{color_subrayado}_{identificador_unico}"
        
        # Se configura el tag con el color y estilo especificados
        self.texto_original.tag_configure(tag_name, underline=True, font=(
            "Arial", 13, "bold"), foreground=color_subrayado)

        # Se aplica el tag al rango seleccionado en el texto
        self.texto_original.tag_add(tag_name, sel_first, sel_last)
        
        # Se eleva la selección para mantener la visibilidad
        self.texto_original.tag_raise("sel")
        
        # Se retorna el nombre del tag creado
        return tag_name

    # --- MÉTODO PARA LIMPIAR EL PANEL DE CITAS ---
    def limpiar_contenido(self):
        # Se elimina todo el contenido del widget de citas
        self.texto_etiquetado.delete(1.0, tk.END)
        # Se notifica al usuario que el contenido ha sido removido
        messagebox.showinfo("Removido", "Las citas del código se han removido.")

    # --- MÉTODO PARA PERSISTENCIA DE SUBRAYADOS ---
    def guardar_subrayados(self):
        # Se verifica si hay una ruta de archivo activa
        if self.ruta:
            nombre_archivo = os.path.basename(self.ruta)
            subrayados = []

            tags_procesados = set()

            # Se recorren las etiquetas para guardar su estado visual actual
            for etiqueta, tag_name in self.etiquetas_asignadas:
                ranges = self.texto_original.tag_ranges(tag_name)
                
                if ranges and tag_name not in tags_procesados:
                    start, end = ranges[0], ranges[1]
                    
                    try:
                        color = self.texto_original.tag_cget(tag_name, "foreground")
                    except:
                        # Fallback por si tag_cget falla al obtener el color
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

            # Se actualiza la entrada en el diccionario de archivos abiertos con los datos más recientes
            self.archivos_abiertos[nombre_archivo] = {
                "contenido": self.contenido,
                "subrayados": subrayados
            }

    def restaurar_subrayados(self):
        pass

    # --- MÉTODO PARA EXPORTAR SOLO FRAGMENTOS ---
    def guardar_etiquetado(self, nuevos_parrafos_etiquetados):
        # Se abre el diálogo para guardar archivo seleccionando la ruta
        ruta_guardado = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Archivos de Texto", "*.txt")])

        if ruta_guardado:
            with open(ruta_guardado, 'w', encoding='utf-8') as archivo_guardado:
                contenido_guardar = ''
                # Se formatea y guarda el contenido etiquetado en el archivo
                for _, sentencia, etiqueta in nuevos_parrafos_etiquetados:
                    contenido_guardar += f">>>({self.etiqueta_actual})<<<\n\n{textwrap.fill(sentencia, width=40)}\n\n"
                archivo_guardado.write(contenido_guardar)
            # Se muestra confirmación de guardado exitoso
            messagebox.showinfo("Guardado", "El fragmento codificado se ha guardado correctamente.")

    # --- MÉTODO PARA EXPORTAR CITAS VISIBLES ---
    def guardar_codificado(self):
        # Se obtiene todo el texto del panel de citas actual
        contenido_editado = self.texto_etiquetado.get(1.0, tk.END)
        # Se abre el diálogo para seleccionar dónde guardar
        ruta_guardado = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Archivos de Texto", "*.txt")])

        # Se aseguran los subrayados actuales antes de proceder
        self.guardar_subrayados()

        if ruta_guardado:
            with open(ruta_guardado, 'w', encoding='utf-8') as archivo_guardado:
                archivo_guardado.write(contenido_editado)
            # Se muestra confirmación de guardado exitoso
            messagebox.showinfo("Guardado", "El fragmento codificado se ha guardado correctamente.")

    # --- MÉTODO DE SALIDA Y CIERRE ---
    def salir_programa(self):
        # Se guardan los subrayados pendientes antes de salir
        self.guardar_subrayados() 
        
        # Se realiza una limpieza de archivos inválidos antes de guardar el estado final
        archivos_validos = {}
        nombres_validos = set()

        for nombre, datos in self.archivos_abiertos.items():
            if datos.get("subrayados"): 
                archivos_validos[nombre] = datos
                nombres_validos.add(nombre)
        
        self.archivos_abiertos = archivos_validos
        
        # Se actualiza el historial conservando solo los archivos válidos
        self.historial_archivos = [
            h for h in self.historial_archivos 
            if h["nombre"] in nombres_validos
        ]
        
        # Se prepara la estructura de datos para la serialización (Pickle)
        datos_a_guardar = {
            "historial_archivos": list(self.historial_archivos),
            "etiquetas_asignadas": [(str(e), str(t)) for e, t in self.etiquetas_asignadas],
            "parrafos_etiquetados": [tuple(map(str, p)) for p in self.parrafos_etiquetados],
            "color_tooltips": dict(self.color_tooltips),
            "indice_navegacion": dict(self.indice_navegacion),
            "archivos_abiertos": {}
        }

        # Se procesan los datos de archivos abiertos para su guardado persistente
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

        # Se escribe el archivo de persistencia 'datos_codificacion.pkl' en disco
        with open("datos_codificacion.pkl", "wb") as archivo:
            pickle.dump(datos_a_guardar, archivo)

        # Se destruye la ventana raíz y se finaliza la ejecución de la aplicación
        self.raiz.destroy()

# --- BLOQUE PRINCIPAL DE EJECUCIÓN ---
if __name__ == "__main__":
    # Se crea la instancia principal de la ventana Tk
    raiz = tk.Tk()
    # Se define la geometría inicial de la ventana
    raiz.geometry("1500x700")  
    # Se instancia la aplicación de etiquetado
    app = EtiquetadoApp(raiz)
    # Se inicia el bucle principal de eventos de la interfaz
    raiz.mainloop()