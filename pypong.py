# =====================================================================
#  PyPong
#  Proyecto de Programacion 1 - Analista de Sistemas
#
#  Juego estilo Pong con 2 palas y 3 pelotas, 10 niveles,
#  registro/login de usuarios y archivos binarios con informes.
# =====================================================================


# =====================================================================
# IMPORTACIONES
# =====================================================================
import struct
import os
import math
import random
from datetime import datetime

try:
    import pygame
except ImportError:
    print("ERROR: no se encontro la libreria pygame.")
    print("Instalela con el comando: pip install pygame")
    raise SystemExit


# =====================================================================
# CONSTANTES
# =====================================================================

# Pantalla
ANCHO = 640
ALTO = 480
FPS = 60
TITULO = "PyPong"

# Colores (R, G, B)
NEGRO = (0, 0, 0)
BLANCO = (255, 255, 255)
GRIS = (110, 110, 110)
ROJO = (220, 50, 50)
VERDE = (50, 200, 80)
AZUL = (60, 120, 255)
AMARILLO = (240, 220, 40)
NARANJA = (255, 150, 30)

# Reglas del juego
VIDAS_INICIALES = 5
NIVEL_MAXIMO = 10
DURACION_TRANSICION = 2000   # milisegundos que dura el cartel "NIVEL X"

# Palas
PALA_ANCHO = 10
PALA_ALTO = 80
VELOCIDAD_JUGADOR = 7
VELOCIDAD_CPU_BASE = 3.5

# Datos iniciales de cada pelota: [radio, color, velocidad X, velocidad Y]
# (las velocidades son las del nivel 1, luego se multiplican segun el nivel)
DATOS_PELOTAS = [
    [8, BLANCO, 3.0, 2.0],
    [10, AMARILLO, 2.5, -2.5],
    [6, NARANJA, 3.5, 1.5],
]

# Archivos binarios
ARCHIVO_USUARIOS = "usuarios.dat"
ARCHIVO_CONTADOR = "contador_partidas.dat"
ARCHIVO_PARTIDAS = "detalle_partidas.dat"
ARCHIVO_COLISIONES = "detalle_colisiones.dat"

# Formato de cada registro (struct): "<" = sin relleno, i = entero de 4 bytes,
# Ns = texto de N bytes. Como todos los registros de un archivo miden lo mismo,
# el registro numero N empieza en el byte N * tamanio y se alcanza con seek.
FORMATO_USUARIOS = struct.Struct("<i50s20s20s")           # Cod_Usuario, NyA, Usuario, Clave
FORMATO_CONTADOR = struct.Struct("<ii")                   # ID, Acum_Partida
FORMATO_PARTIDAS = struct.Struct("<iiiii19si")            # ID_PAR_JUGADOR, Cod_Usuario, Num_Partida,
                                                          # Puntaje_A, Puntaje_B, Fecha, Nivel
FORMATO_COLISIONES = struct.Struct("<iii19sii30s")        # ID_COLISION, Cod_Usuario, Num_Partida, Fecha,
                                                          # X, Y, Observacion

# Largos maximos de los campos de texto de usuarios
MAX_NYA = 50
MAX_USUARIO = 20
MAX_CLAVE = 20


# =====================================================================
#  GESTION DE ARCHIVOS BINARIOS (registros de tamanio fijo + seek)
# =====================================================================

def crear_archivo_si_no_existe(nombre_archivo):
    """Crea el archivo vacio solamente si todavia no existe."""
    archivo = open(nombre_archivo, "ab")
    archivo.close()


def inicializar_archivos():
    """Crea todos los archivos binarios necesarios al iniciar el programa."""
    crear_archivo_si_no_existe(ARCHIVO_USUARIOS)
    crear_archivo_si_no_existe(ARCHIVO_CONTADOR)
    crear_archivo_si_no_existe(ARCHIVO_PARTIDAS)
    crear_archivo_si_no_existe(ARCHIVO_COLISIONES)

    # El contador ademas necesita su registro inicial: 1,0
    if os.path.getsize(ARCHIVO_CONTADOR) == 0:
        escribir_contador(0)


def texto_a_bytes(texto):
    """Convierte un texto a bytes para guardarlo en un campo de tamanio fijo
    (struct lo completa con ceros o lo corta si sobra)."""
    return texto.encode("utf-8")


def bytes_a_texto(datos):
    """Convierte un campo de tamanio fijo otra vez a texto (saca los ceros)."""
    return datos.rstrip(b"\x00").decode("utf-8", errors="replace")


def cantidad_registros(nombre_archivo, formato):
    """Cantidad de registros = tamanio del archivo / tamanio de cada registro."""
    if not os.path.exists(nombre_archivo):
        return 0
    return os.path.getsize(nombre_archivo) // formato.size


def leer_registros(nombre_archivo, formato):
    """Devuelve una lista con todos los registros (tuplas) del archivo.
    Solo se usa cuando hay que recorrer todo: busquedas e informes."""
    registros = []
    try:
        archivo = open(nombre_archivo, "rb")
    except FileNotFoundError:
        return registros

    datos = archivo.read(formato.size)
    while len(datos) == formato.size:
        registros.append(formato.unpack(datos))
        datos = archivo.read(formato.size)
    archivo.close()
    return registros


def leer_registro_en(nombre_archivo, formato, posicion):
    """Lee un solo registro usando seek. La posicion 0 es el primer registro.
    Devuelve None si esa posicion no existe."""
    if posicion < 0 or posicion >= cantidad_registros(nombre_archivo, formato):
        return None
    archivo = open(nombre_archivo, "rb")
    archivo.seek(posicion * formato.size)
    datos = archivo.read(formato.size)
    archivo.close()
    return formato.unpack(datos)


def leer_ultimo_registro(nombre_archivo, formato):
    """Lee el ultimo registro saltando directo al final. None si no hay registros."""
    cantidad = cantidad_registros(nombre_archivo, formato)
    if cantidad == 0:
        return None
    return leer_registro_en(nombre_archivo, formato, cantidad - 1)


def agregar_registro(nombre_archivo, formato, valores):
    """Agrega un registro al final del archivo."""
    archivo = open(nombre_archivo, "ab")
    archivo.write(formato.pack(*valores))
    archivo.close()


def obtener_proximo_id(nombre_archivo, formato):
    """Los IDs se asignan en orden, asi que el ultimo registro tiene el mayor.
    Se lee solo ese registro (con seek) y se devuelve su ID + 1. Si no hay, 1."""
    ultimo = leer_ultimo_registro(nombre_archivo, formato)
    if ultimo is None:
        return 1
    return ultimo[0] + 1


def obtener_fecha_actual():
    """Devuelve la fecha y hora actual como texto."""
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


# =====================================================================
# USUARIOS
# =====================================================================
# Cada usuario es una fila: [Cod_Usuario, NyA, Usuario, Clave]

def registro_a_usuario(registro):
    """Convierte el registro binario en la lista [cod, NyA, usuario, clave]."""
    return [registro[0], bytes_a_texto(registro[1]), bytes_a_texto(registro[2]),
            bytes_a_texto(registro[3])]


def buscar_usuario_por_nombre(nombre_usuario):
    """Devuelve el usuario o None si no existe (sin distinguir mayusculas).
    Hay que recorrer el archivo porque el nombre no indica la posicion."""
    for registro in leer_registros(ARCHIVO_USUARIOS, FORMATO_USUARIOS):
        usuario = registro_a_usuario(registro)
        if usuario[2].lower() == nombre_usuario.lower():
            return usuario
    return None


def buscar_usuario_por_codigo(cod_usuario):
    """Devuelve el usuario con ese codigo o None si no existe.
    Los codigos son 1, 2, 3... asi que el usuario N esta en la posicion N-1:
    se salta directo con seek, sin recorrer el archivo."""
    registro = leer_registro_en(ARCHIVO_USUARIOS, FORMATO_USUARIOS, cod_usuario - 1)
    if registro is None or registro[0] != cod_usuario:
        return None
    return registro_a_usuario(registro)


# =====================================================================
# REGISTRO Y LOGIN
# =====================================================================

def registrar_usuario():
    print()
    print("----- REGISTRAR USUARIO -----")
    nombre_apellido = input("Nombre y Apellido: ").strip()
    nombre_usuario = input("Usuario: ").strip()
    clave = input("Clave: ").strip()

    # Validaciones basicas
    if nombre_apellido == "" or nombre_usuario == "" or clave == "":
        print("ERROR: ningun campo puede estar vacio.")
        return

    if buscar_usuario_por_nombre(nombre_usuario) is not None:
        print("ERROR: el usuario '" + nombre_usuario + "' ya existe.")
        return

    # Los campos de texto tienen un tamanio fijo dentro del archivo binario
    if (len(texto_a_bytes(nombre_apellido)) > MAX_NYA or len(texto_a_bytes(nombre_usuario)) > MAX_USUARIO
            or len(texto_a_bytes(clave)) > MAX_CLAVE):
        print("ERROR: maximo", MAX_NYA, "caracteres para el nombre,", MAX_USUARIO,
              "para el usuario y", MAX_CLAVE, "para la clave.")
        return

    codigo = obtener_proximo_id(ARCHIVO_USUARIOS, FORMATO_USUARIOS)
    agregar_registro(ARCHIVO_USUARIOS, FORMATO_USUARIOS,
                     [codigo, texto_a_bytes(nombre_apellido), texto_a_bytes(nombre_usuario),
                      texto_a_bytes(clave)])
    print("Usuario registrado correctamente. Su codigo de usuario es:", codigo)


def iniciar_sesion():
    """Pide usuario y clave. Devuelve el codigo del usuario o 0 si fallo."""
    print()
    print("----- INICIAR SESION -----")
    nombre_usuario = input("Usuario: ").strip()
    clave = input("Clave: ").strip()

    usuario = buscar_usuario_por_nombre(nombre_usuario)
    if usuario is None or usuario[3] != clave:
        print("ERROR: usuario o clave incorrectos.")
        return 0

    print("Bienvenido/a " + usuario[1] + "!")
    return usuario[0]


# =====================================================================
# PARTIDAS
# =====================================================================

def escribir_contador(valor):
    """Escribe el contador en el unico registro del archivo (posicion 0).
    Con seek(0) se pisa ese registro sin reescribir el archivo entero."""
    try:
        archivo = open(ARCHIVO_CONTADOR, "r+b")
    except FileNotFoundError:
        archivo = open(ARCHIVO_CONTADOR, "wb")
    archivo.seek(0)
    archivo.write(FORMATO_CONTADOR.pack(1, valor))
    archivo.close()


def leer_contador():
    """Devuelve el valor acumulado del contador (0 si el archivo esta vacio)."""
    registro = leer_registro_en(ARCHIVO_CONTADOR, FORMATO_CONTADOR, 0)
    if registro is None:
        return 0
    return registro[1]


def obtener_mayor_num_partida():
    """Devuelve el numero de partida mas alto guardado en detalle_partidas.dat.
    Los numeros se asignan en orden creciente, asi que alcanza con leer el
    ultimo registro (seek al final) sin recorrer todo el archivo."""
    ultimo = leer_ultimo_registro(ARCHIVO_PARTIDAS, FORMATO_PARTIDAS)
    if ultimo is None:
        return 0
    return ultimo[2]


def incrementar_contador_partidas():
    """Suma 1 al contador general y devuelve el nuevo numero de partida."""
    valor = leer_contador()

    # Si el contador se borro o se rompio, no repetimos numeros ya usados
    mayor_guardado = obtener_mayor_num_partida()
    if valor < mayor_guardado:
        valor = mayor_guardado

    valor = valor + 1
    escribir_contador(valor)
    return valor


def guardar_partida(cod_usuario, num_partida, puntaje_a, puntaje_b, nivel):
    """Agrega un registro a detalle_partidas.dat."""
    id_partida = obtener_proximo_id(ARCHIVO_PARTIDAS, FORMATO_PARTIDAS)
    agregar_registro(ARCHIVO_PARTIDAS, FORMATO_PARTIDAS,
                     [id_partida, cod_usuario, num_partida, puntaje_a, puntaje_b,
                      texto_a_bytes(obtener_fecha_actual()), nivel])


# =====================================================================
# COLISIONES
# =====================================================================

def registrar_colision(colisiones, cod_usuario, num_partida, x, y, observacion):
    """Anota un evento en la lista de colisiones (se guarda en el archivo al final).
    Ejemplos de observacion: 'Colision Pala1 Pelota2' o 'Perdida Izquierda Pelota3'."""
    colisiones.append([cod_usuario, num_partida, obtener_fecha_actual(),
                       int(x), int(y), observacion])


def guardar_colisiones(colisiones):
    """Escribe en detalle_colisiones.dat todas las colisiones anotadas en la partida.
    El archivo se abre una sola vez y el proximo ID se calcula una sola vez."""
    id_colision = obtener_proximo_id(ARCHIVO_COLISIONES, FORMATO_COLISIONES)
    archivo = open(ARCHIVO_COLISIONES, "ab")
    for c in colisiones:
        archivo.write(FORMATO_COLISIONES.pack(id_colision, c[0], c[1],
                                              texto_a_bytes(c[2]), c[3], c[4],
                                              texto_a_bytes(c[5])))
        id_colision = id_colision + 1
    archivo.close()


# =====================================================================
# CLASE BASE (herencia sencilla)
# =====================================================================

class ObjetoJuego:
    """Clase padre de Pala y Pelota: todo objeto tiene posicion y color."""

    def __init__(self, nombre, x, y, color):
        self.nombre = nombre
        self.x = x
        self.y = y
        self.color = color

    def dibujar(self, pantalla):
        pass   # cada clase hija lo implementa a su manera


# =====================================================================
# CLASE PALA
# =====================================================================

class Pala(ObjetoJuego):

    def __init__(self, nombre, x, y, color):
        super().__init__(nombre, x, y, color)
        self.ancho = PALA_ANCHO
        self.alto = PALA_ALTO

    def mover(self, desplazamiento):
        """Mueve la pala en vertical sin salir de la pantalla."""
        self.y = self.y + desplazamiento
        if self.y < 0:
            self.y = 0
        if self.y + self.alto > ALTO:
            self.y = ALTO - self.alto

    def centro_y(self):
        return self.y + self.alto / 2

    def obtener_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.ancho, self.alto)

    def dibujar(self, pantalla):
        pygame.draw.rect(pantalla, self.color, self.obtener_rect())


# =====================================================================
# CLASE PELOTA
# =====================================================================

class Pelota(ObjetoJuego):

    def __init__(self, nombre, radio, color, vel_base_x, vel_base_y):
        super().__init__(nombre, ANCHO / 2, ALTO / 2, color)
        self.radio = radio
        self.vel_base_x = vel_base_x     # velocidad en el nivel 1
        self.vel_base_y = vel_base_y
        self.vel_x = 0
        self.vel_y = 0

    def reiniciar(self, nivel):
        """Vuelve a poner la pelota en el centro con la velocidad de su nivel
        y una direccion al azar."""
        multiplicador = calcular_multiplicador(nivel)
        self.x = ANCHO / 2
        self.y = random.randint(100, ALTO - 100)
        self.vel_x = self.vel_base_x * multiplicador * random.choice([-1, 1])
        self.vel_y = self.vel_base_y * multiplicador * random.choice([-1, 1])

    def mover(self):
        self.x = self.x + self.vel_x
        self.y = self.y + self.vel_y

    def rebotar_techo_piso(self):
        if self.y - self.radio <= 0:
            self.y = self.radio
            self.vel_y = abs(self.vel_y)
        elif self.y + self.radio >= ALTO:
            self.y = ALTO - self.radio
            self.vel_y = -abs(self.vel_y)

    def obtener_rect(self):
        return pygame.Rect(int(self.x - self.radio), int(self.y - self.radio),
                           self.radio * 2, self.radio * 2)

    def rebotar_en_pala(self, pala):
        """Si la pelota toca la pala y viene hacia ella, rebota.
        Devuelve True si hubo colision, False si no."""
        if not self.obtener_rect().colliderect(pala.obtener_rect()):
            return False

        mitad_pala = pala.x + pala.ancho / 2
        if pala.nombre == "Pala1":
            if self.vel_x >= 0:          # ya se esta alejando
                return False
            if self.x < mitad_pala:      # ya paso la pala: no se la rescata
                return False
            self.vel_x = abs(self.vel_x)
            self.x = pala.x + pala.ancho + self.radio
        else:
            if self.vel_x <= 0:
                return False
            if self.x > mitad_pala:
                return False
            self.vel_x = -abs(self.vel_x)
            self.x = pala.x - self.radio

        # Cambio sencillo de direccion segun en que tercio de la pala pego
        tercio = pala.alto / 3
        if self.y < pala.y + tercio:
            self.vel_y = -abs(self.vel_y)
        elif self.y > pala.y + 2 * tercio:
            self.vel_y = abs(self.vel_y)
        return True

    def salio_por_izquierda(self):
        return self.x + self.radio < 0

    def salio_por_derecha(self):
        return self.x - self.radio > ANCHO

    def dibujar(self, pantalla):
        pygame.draw.circle(pantalla, self.color, (int(self.x), int(self.y)), self.radio)


# =====================================================================
# CLASE TEXTO
# =====================================================================

class Texto:

    def __init__(self, tamanio):
        self.fuente = pygame.font.Font(None, tamanio)   # fuente por defecto de pygame

    def dibujar(self, pantalla, mensaje, x, y, color, centrado):
        superficie = self.fuente.render(mensaje, True, color)
        rect = superficie.get_rect()
        if centrado:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        pantalla.blit(superficie, rect)


# =====================================================================
# FUNCIONES AUXILIARES
# =====================================================================

def calcular_multiplicador(nivel):
    """Nivel 1 -> 1.00, nivel 2 -> 1.25, ... nivel 10 -> 3.25"""
    return 1 + (nivel - 1) * 0.25


def restar_sin_negativos(valor):
    """Resta 1 pero nunca deja el valor por debajo de 0."""
    if valor > 0:
        return valor - 1
    return 0


def crear_pelotas(nivel):
    """Crea las 3 pelotas (Pelota1, Pelota2, Pelota3) para el nivel indicado."""
    pelotas = []
    for i in range(len(DATOS_PELOTAS)):
        radio = DATOS_PELOTAS[i][0]
        color = DATOS_PELOTAS[i][1]
        vel_base_x = DATOS_PELOTAS[i][2]
        vel_base_y = DATOS_PELOTAS[i][3]
        nombre = "Pelota" + str(i + 1)
        pelota = Pelota(nombre, radio, color, vel_base_x, vel_base_y)
        pelota.reiniciar(nivel)
        pelota.y = ALTO / 2 + (i - 1) * 100     # al empezar, separadas verticalmente
        pelotas.append(pelota)
    return pelotas


def controlar_choque_entre_pelotas(pelota_a, pelota_b):
    """Si dos pelotas se tocan, intercambian sus velocidades y se separan."""
    dx = pelota_b.x - pelota_a.x
    dy = pelota_b.y - pelota_a.y
    distancia = math.sqrt(dx * dx + dy * dy)
    suma_radios = pelota_a.radio + pelota_b.radio

    if distancia >= suma_radios:
        return   # no se tocan

    # Donde estaran en el proximo paso
    futura_dx = (pelota_b.x + pelota_b.vel_x) - (pelota_a.x + pelota_a.vel_x)
    futura_dy = (pelota_b.y + pelota_b.vel_y) - (pelota_a.y + pelota_a.vel_y)
    distancia_futura = math.sqrt(futura_dx * futura_dx + futura_dy * futura_dy)

    if distancia_futura > distancia:
        return   # ya se estan separando, no hace falta rebotar

    # Intercambio de velocidades
    auxiliar_x = pelota_a.vel_x
    auxiliar_y = pelota_a.vel_y
    pelota_a.vel_x = pelota_b.vel_x
    pelota_a.vel_y = pelota_b.vel_y
    pelota_b.vel_x = auxiliar_x
    pelota_b.vel_y = auxiliar_y

    # Separarlas para que no queden superpuestas
    if distancia == 0:
        dx = 1
        dy = 0
        distancia = 1
    superposicion = suma_radios - distancia
    mover_x = dx / distancia * (superposicion / 2 + 1)
    mover_y = dy / distancia * (superposicion / 2 + 1)
    pelota_a.x = pelota_a.x - mover_x
    pelota_a.y = pelota_a.y - mover_y
    pelota_b.x = pelota_b.x + mover_x
    pelota_b.y = pelota_b.y + mover_y

    # Que no queden fuera de la pantalla por la separacion
    pelota_a.rebotar_techo_piso()
    pelota_b.rebotar_techo_piso()


def elegir_pelota_amenaza(pelotas, pala_cpu):
    """La amenaza es la pelota que va hacia la derecha y esta mas cerca de la CPU."""
    amenaza = None
    for pelota in pelotas:
        if pelota.vel_x > 0 and pelota.x < pala_cpu.x:
            if amenaza is None or pelota.x > amenaza.x:
                amenaza = pelota
    return amenaza


def mover_cpu(pala_cpu, pelotas, nivel):
    """IA sencilla: la pala sigue la altura de la pelota amenaza."""
    velocidad = VELOCIDAD_CPU_BASE + (nivel - 1) * 0.4
    amenaza = elegir_pelota_amenaza(pelotas, pala_cpu)

    if amenaza is None:
        objetivo = ALTO / 2          # sin amenaza vuelve al centro
    else:
        objetivo = amenaza.y

    centro = pala_cpu.centro_y()
    if objetivo < centro - 10:
        pala_cpu.mover(-velocidad)
    elif objetivo > centro + 10:
        pala_cpu.mover(velocidad)


def dibujar_linea_central(pantalla):
    for y in range(0, ALTO, 20):
        pygame.draw.rect(pantalla, GRIS, (ANCHO // 2 - 1, y, 2, 10))


def dibujar_vidas(pantalla, vidas, x_inicial, color):
    """Dibuja un circulo pequeño por cada vida."""
    for i in range(vidas):
        pygame.draw.circle(pantalla, color, (x_inicial + i * 16, 42), 6)


def dibujar_marcador(pantalla, texto, nivel, vidas_jugador, vidas_cpu, puntaje_a, puntaje_b):
    texto.dibujar(pantalla, "JUGADOR  Vidas: " + str(vidas_jugador), 10, 10, VERDE, False)
    dibujar_vidas(pantalla, vidas_jugador, 16, VERDE)

    texto.dibujar(pantalla, "CPU  Vidas: " + str(vidas_cpu), ANCHO - 140, 10, AZUL, False)
    dibujar_vidas(pantalla, vidas_cpu, ANCHO - 134, AZUL)

    texto.dibujar(pantalla, "Nivel " + str(nivel), ANCHO // 2, 20, BLANCO, True)

    texto.dibujar(pantalla, "Puntaje A: " + str(puntaje_a), 10, ALTO - 25, BLANCO, False)
    texto.dibujar(pantalla, "Puntaje B: " + str(puntaje_b), ANCHO - 130, ALTO - 25, BLANCO, False)
    texto.dibujar(pantalla, "P = Pausa   ESC = Salir", ANCHO // 2, ALTO - 15, GRIS, True)


def dibujar_pantalla_final(pantalla, texto_grande, texto_chico, titulo, color,
                           nivel, puntaje_a, puntaje_b):
    """Pantalla de Game Over o de Victoria."""
    pantalla.fill(NEGRO)
    texto_grande.dibujar(pantalla, titulo, ANCHO // 2, 150, color, True)
    texto_chico.dibujar(pantalla, "Nivel alcanzado: " + str(nivel), ANCHO // 2, 230, BLANCO, True)
    texto_chico.dibujar(pantalla, "Puntaje A: " + str(puntaje_a) + "   Puntaje B: " + str(puntaje_b),
                        ANCHO // 2, 260, BLANCO, True)
    texto_chico.dibujar(pantalla, "Partida guardada", ANCHO // 2, 300, GRIS, True)
    texto_chico.dibujar(pantalla, "Presione ENTER o ESC para volver al menu",
                        ANCHO // 2, 360, AMARILLO, True)


def dibujar_juego(pantalla, pala1, pala2, pelotas):
    """Dibuja la cancha, las 2 palas y las 3 pelotas.
    Cada objeto sabe dibujarse solo (metodo dibujar de cada clase)."""
    pantalla.fill(NEGRO)
    dibujar_linea_central(pantalla)
    pala1.dibujar(pantalla)
    pala2.dibujar(pantalla)
    for pelota in pelotas:
        pelota.dibujar(pantalla)


def dibujar_cartel_nivel(pantalla, texto_grande, texto_medio, nivel):
    """Cartel que aparece al empezar cada nivel."""
    velocidad = "Velocidad x" + format(calcular_multiplicador(nivel), ".2f")
    texto_grande.dibujar(pantalla, "NIVEL " + str(nivel), ANCHO // 2, 200, AMARILLO, True)
    texto_medio.dibujar(pantalla, velocidad, ANCHO // 2, 260, BLANCO, True)


def dibujar_cartel_pausa(pantalla, texto_grande, texto_chico):
    texto_grande.dibujar(pantalla, "PAUSA", ANCHO // 2, 200, AMARILLO, True)
    texto_chico.dibujar(pantalla, "Presione P para continuar", ANCHO // 2, 260, BLANCO, True)


# =====================================================================
# BUCLE PRINCIPAL DEL JUEGO
# =====================================================================

def jugar(cod_usuario):
    num_partida = incrementar_contador_partidas()
    print("Comienza la partida numero", num_partida)

    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption(TITULO)
    reloj = pygame.time.Clock()

    texto_chico = Texto(26)
    texto_medio = Texto(40)
    texto_grande = Texto(72)

    # Los 5 objetos principales del juego
    pala1 = Pala("Pala1", 20, ALTO / 2 - PALA_ALTO / 2, VERDE)
    pala2 = Pala("Pala2", ANCHO - 20 - PALA_ANCHO, ALTO / 2 - PALA_ALTO / 2, AZUL)
    nivel = 1
    pelotas = crear_pelotas(nivel)

    vidas_jugador = VIDAS_INICIALES
    vidas_cpu = VIDAS_INICIALES
    puntaje_a = 0
    puntaje_b = 0

    # Estados posibles: "transicion", "jugando", "game_over", "victoria"
    estado = "transicion"
    inicio_transicion = pygame.time.get_ticks()
    pausado = False
    partida_guardada = False
    ejecutando = True

    # Las colisiones se anotan aca durante el juego y se guardan al final
    colisiones = []

    # finally: lo que esta ahi se ejecuta SIEMPRE, aunque el juego termine con un error
    try:
        while ejecutando:
            reloj.tick(FPS)

            # ---------- EVENTOS ----------
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    ejecutando = False
                elif evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_ESCAPE:
                        ejecutando = False
                    elif evento.key == pygame.K_p and estado == "jugando":
                        pausado = not pausado
                    elif evento.key == pygame.K_RETURN:
                        if estado == "game_over" or estado == "victoria":
                            ejecutando = False

            # ---------- LOGICA ----------
            if estado == "transicion":
                if pygame.time.get_ticks() - inicio_transicion >= DURACION_TRANSICION:
                    estado = "jugando"

            elif estado == "jugando" and not pausado:
                # Pala del jugador
                teclas = pygame.key.get_pressed()
                if teclas[pygame.K_UP]:
                    pala1.mover(-VELOCIDAD_JUGADOR)
                if teclas[pygame.K_DOWN]:
                    pala1.mover(VELOCIDAD_JUGADOR)

                # Pala de la CPU
                mover_cpu(pala2, pelotas, nivel)

                # Pelotas
                for pelota in pelotas:
                    pelota.mover()
                    pelota.rebotar_techo_piso()

                    if pelota.rebotar_en_pala(pala1):
                        puntaje_a = puntaje_a + 1
                        registrar_colision(colisiones, cod_usuario, num_partida, pelota.x, pelota.y,
                                           "Colision Pala1 " + pelota.nombre)
                    elif pelota.rebotar_en_pala(pala2):
                        puntaje_b = puntaje_b + 1
                        registrar_colision(colisiones, cod_usuario, num_partida, pelota.x, pelota.y,
                                           "Colision Pala2 " + pelota.nombre)

                    if pelota.salio_por_izquierda():
                        registrar_colision(colisiones, cod_usuario, num_partida, pelota.x, pelota.y,
                                           "Perdida Izquierda " + pelota.nombre)
                        vidas_jugador = restar_sin_negativos(vidas_jugador)
                        puntaje_a = restar_sin_negativos(puntaje_a)
                        pelota.reiniciar(nivel)
                    elif pelota.salio_por_derecha():
                        registrar_colision(colisiones, cod_usuario, num_partida, pelota.x, pelota.y,
                                           "Perdida Derecha " + pelota.nombre)
                        vidas_cpu = restar_sin_negativos(vidas_cpu)
                        puntaje_b = restar_sin_negativos(puntaje_b)
                        pelota.reiniciar(nivel)

                # Choques entre pelotas (cada par se revisa una sola vez)
                for i in range(len(pelotas)):
                    for j in range(i + 1, len(pelotas)):
                        controlar_choque_entre_pelotas(pelotas[i], pelotas[j])

                # ¿Termino el nivel o la partida?
                if vidas_jugador == 0:
                    estado = "game_over"
                elif vidas_cpu == 0:
                    if nivel < NIVEL_MAXIMO:
                        nivel = nivel + 1
                        vidas_jugador = VIDAS_INICIALES
                        vidas_cpu = VIDAS_INICIALES
                        pelotas = crear_pelotas(nivel)
                        estado = "transicion"
                        inicio_transicion = pygame.time.get_ticks()
                    else:
                        estado = "victoria"

                # Guardar apenas termina por Game Over o Victoria
                if (estado == "game_over" or estado == "victoria") and not partida_guardada:
                    guardar_partida(cod_usuario, num_partida, puntaje_a, puntaje_b, nivel)
                    guardar_colisiones(colisiones)
                    partida_guardada = True

            # ---------- DIBUJO ----------
            if estado == "game_over":
                dibujar_pantalla_final(pantalla, texto_grande, texto_chico, "GAME OVER", ROJO,
                                       nivel, puntaje_a, puntaje_b)
            elif estado == "victoria":
                dibujar_pantalla_final(pantalla, texto_grande, texto_chico, "VICTORIA!", VERDE,
                                       nivel, puntaje_a, puntaje_b)
            else:
                dibujar_juego(pantalla, pala1, pala2, pelotas)
                dibujar_marcador(pantalla, texto_chico, nivel, vidas_jugador, vidas_cpu,
                                 puntaje_a, puntaje_b)
                if estado == "transicion":
                    dibujar_cartel_nivel(pantalla, texto_grande, texto_medio, nivel)
                elif pausado:
                    dibujar_cartel_pausa(pantalla, texto_grande, texto_chico)

            pygame.display.flip()

    finally:
        pygame.quit()
        # Si se salio con ESC, cerrando la ventana o por un error, se guarda aqui (una sola vez)
        if not partida_guardada:
            guardar_partida(cod_usuario, num_partida, puntaje_a, puntaje_b, nivel)
            guardar_colisiones(colisiones)
            partida_guardada = True

    print("Partida", num_partida, "guardada. Puntaje A:", puntaje_a,
          "- Puntaje B:", puntaje_b, "- Nivel:", nivel)


# =====================================================================
# INFORMES
# =====================================================================

def pedir_entero(mensaje):
    """Pide un numero entero mayor que 0 hasta que el usuario lo ingrese bien."""
    while True:
        texto = input(mensaje).strip()
        try:
            numero = int(texto)
            if numero > 0:
                return numero
            print("Debe ingresar un numero mayor que 0.")
        except ValueError:
            print("Debe ingresar un numero entero.")


def informe_movimientos():
    print()
    print("===== INFORME 1: MOVIMIENTOS POR USUARIO Y PARTIDA =====")
    cod_usuario = pedir_entero("Codigo de Usuario: ")
    num_partida = pedir_entero("Numero de Partida: ")

    usuario = buscar_usuario_por_codigo(cod_usuario)
    if usuario is None:
        print("No existe un usuario con el codigo", cod_usuario)
        return

    print()
    print("Usuario:", cod_usuario, "-", usuario[1], "   Partida:", num_partida)
    print("-" * 78)
    print(f"{'Cod':<5}{'Nombre y Apellido':<22}{'Part.':<7}{'Fecha':<21}{'X,Y':<11}{'Observacion'}")
    print("-" * 78)

    total = 0
    for r in leer_registros(ARCHIVO_COLISIONES, FORMATO_COLISIONES):
        # r = (id, cod_usuario, num_partida, fecha, x, y, observacion)
        if r[1] == cod_usuario and r[2] == num_partida:
            coordenada = str(r[4]) + "," + str(r[5])
            print(f"{r[1]:<5}{usuario[1][:20]:<22}{r[2]:<7}{bytes_a_texto(r[3]):<21}"
                  f"{coordenada:<11}{bytes_a_texto(r[6])}")
            total = total + 1

    if total == 0:
        print("No hay registros para ese usuario y partida.")
    print("-" * 78)
    print("Total General Colisiones:", total)


def informe_ranking():
    print()
    print("===== INFORME 2: RANKING POR USUARIO =====")
    cod_usuario = pedir_entero("Codigo de Usuario: ")

    usuario = buscar_usuario_por_codigo(cod_usuario)
    if usuario is None:
        print("No existe un usuario con el codigo", cod_usuario)
        return

    # Juntamos las partidas del usuario: [num_partida, puntaje_a, puntaje_b, total, nivel, fecha]
    partidas = []
    for r in leer_registros(ARCHIVO_PARTIDAS, FORMATO_PARTIDAS):
        # r = (id, cod_usuario, num_partida, puntaje_a, puntaje_b, fecha, nivel)
        if r[1] == cod_usuario:
            total = r[3] + r[4]
            partidas.append([r[2], r[3], r[4], total, r[6], bytes_a_texto(r[5])])

    print()
    print("Usuario:", cod_usuario, "-", usuario[1])
    if len(partidas) == 0:
        print("El usuario todavia no tiene partidas registradas.")
        return

    print("-" * 60)
    print(f"{'Part.':<8}{'Punt.A':<9}{'Punt.B':<9}{'Total':<8}{'Nivel':<7}{'Fecha'}")
    print("-" * 60)

    total_a = 0
    total_b = 0
    mejor = partidas[0]
    peor = partidas[0]
    for partida in partidas:
        print(f"{partida[0]:<8}{partida[1]:<9}{partida[2]:<9}{partida[3]:<8}{partida[4]:<7}{partida[5]}")
        total_a = total_a + partida[1]
        total_b = total_b + partida[2]
        if partida[3] > mejor[3]:
            mejor = partida
        if partida[3] < peor[3]:
            peor = partida

    print("-" * 60)
    print("Total Puntaje A:", total_a)
    print("Total Puntaje B:", total_b)
    print("Total General:  ", total_a + total_b)
    print("Mejor partida:   Partida", mejor[0], "con", mejor[3], "puntos")
    print("Peor partida:    Partida", peor[0], "con", peor[3], "puntos")


def obtener_posicion_en_matriz(observacion):
    """A partir de 'Colision Pala2 Pelota3' devuelve fila 1 y columna 2.
    Si la observacion no es una colision con pala devuelve -1, -1."""
    partes = observacion.split()
    if len(partes) != 3 or partes[0] != "Colision":
        return -1, -1

    fila = -1
    if partes[1] == "Pala1":
        fila = 0
    elif partes[1] == "Pala2":
        fila = 1

    columna = -1
    if partes[2] == "Pelota1":
        columna = 0
    elif partes[2] == "Pelota2":
        columna = 1
    elif partes[2] == "Pelota3":
        columna = 2

    return fila, columna


def informe_matriz():
    print()
    print("===== INFORME 3: MATRIZ DE COLISIONES (PALA x PELOTA) =====")
    cod_usuario = pedir_entero("Codigo de Usuario: ")
    num_partida = pedir_entero("Numero de Partida: ")

    usuario = buscar_usuario_por_codigo(cod_usuario)
    if usuario is None:
        print("No existe un usuario con el codigo", cod_usuario)
        return

    # Matriz de 2 filas (palas) x 3 columnas (pelotas), todo en 0
    matriz = [[0, 0, 0],
              [0, 0, 0]]

    for r in leer_registros(ARCHIVO_COLISIONES, FORMATO_COLISIONES):
        # r = (id, cod_usuario, num_partida, fecha, x, y, observacion)
        if r[1] == cod_usuario and r[2] == num_partida:
            fila, columna = obtener_posicion_en_matriz(bytes_a_texto(r[6]))
            if fila != -1 and columna != -1:
                matriz[fila][columna] = matriz[fila][columna] + 1

    nombres_palas = ["Pala1", "Pala2"]
    totales_columnas = [0, 0, 0]
    total_general = 0

    print()
    print("Usuario:", cod_usuario, "-", usuario[1], "   Partida:", num_partida)
    print("-" * 58)
    print(f"{'Objeto':<12}{'Pelota 1':>10}{'Pelota 2':>10}{'Pelota 3':>10}{'Total':>10}")
    print("-" * 58)
    for i in range(2):
        total_pala = 0
        for j in range(3):
            total_pala = total_pala + matriz[i][j]
            totales_columnas[j] = totales_columnas[j] + matriz[i][j]
        total_general = total_general + total_pala
        print(f"{nombres_palas[i]:<12}{matriz[i][0]:>10}{matriz[i][1]:>10}{matriz[i][2]:>10}{total_pala:>10}")
    print("-" * 58)
    print(f"{'Total':<12}{totales_columnas[0]:>10}{totales_columnas[1]:>10}{totales_columnas[2]:>10}{total_general:>10}")

    if total_general == 0:
        print("No hay colisiones con palas registradas para ese usuario y partida.")


# =====================================================================
# MENU DE INFORMES
# =====================================================================

def menu_informes():
    opcion = ""
    while opcion != "4":
        print()
        print("========== MENU DE INFORMES ==========")
        print("1. Movimientos por Usuario y Partida")
        print("2. Ranking por Usuario")
        print("3. Matrices de Colisiones (Pala x Pelota)")
        print("4. Volver")
        opcion = input("Elija una opcion: ").strip()

        if opcion == "1":
            informe_movimientos()
        elif opcion == "2":
            informe_ranking()
        elif opcion == "3":
            informe_matriz()
        elif opcion != "4":
            print("Opcion invalida.")


# =====================================================================
# MENU PRINCIPAL
# =====================================================================

def menu_principal():
    inicializar_archivos()
    opcion = ""
    while opcion != "4":
        print()
        print("========== PYPONG ==========")
        print("1. Registrar Usuario")
        print("2. Iniciar Sesion y Jugar")
        print("3. Informes")
        print("4. Salir")
        opcion = input("Elija una opcion: ").strip()

        if opcion == "1":
            registrar_usuario()
        elif opcion == "2":
            cod_usuario = iniciar_sesion()
            if cod_usuario != 0:
                jugar(cod_usuario)
        elif opcion == "3":
            menu_informes()
        elif opcion == "4":
            print("Hasta luego!")
        else:
            print("Opcion invalida.")


# =====================================================================
# PUNTO DE ENTRADA
# =====================================================================

if __name__ == "__main__":
    menu_principal()
