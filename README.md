# PyPong (método punteros)

Trabajo final de la materia **Programación 1**, Año 2026, del profesor **Coqui**, en la **Escuela Normal 10**.

**Integrantes del proyecto:** Gustavo Godoy y Rodrigo Mutuberria.

---

## Descripción

PyPong es un juego estilo Pong hecho en Python con la librería [pygame](https://www.pygame.org/). El jugador controla una pala contra una CPU, pero en lugar de una sola pelota hay **tres pelotas** al mismo tiempo, cada una con distinto tamaño, color y velocidad. El juego tiene **10 niveles** que se vuelven cada vez más rápidos, registro e inicio de sesión de usuarios y archivos binarios donde se guarda todo el historial para generar informes.

El método de acceso a los archivos binarios es el de los **punteros**: todos los registros de un archivo tienen el mismo tamaño, por lo que el registro número N empieza en el byte `N * tamaño` y se alcanza directamente con `seek`, sin recorrer el archivo.

## Requisitos

- Python 3
- pygame

```bash
pip install pygame
```

## Cómo ejecutarlo

```bash
python pypong.py
```

Los archivos `.dat` se crean solos la primera vez que se ejecuta el programa.

## Menú principal

1. **Registrar Usuario**: pide nombre y apellido, usuario y clave. Cada usuario recibe un código numérico.
2. **Iniciar Sesión y Jugar**: valida usuario y clave y empieza una partida.
3. **Informes**: muestra los informes generados a partir de los archivos.
4. **Salir**

## Cómo se juega

| Tecla | Acción |
|-------|--------|
| ↑ / ↓ | Mover la pala del jugador (verde, izquierda) |
| P | Pausar / continuar |
| ESC | Salir de la partida (se guarda igual) |
| ENTER | Volver al menú en la pantalla de Game Over o Victoria |

- El jugador (pala verde, izquierda) se enfrenta a la **CPU** (pala azul, derecha).
- Hay **3 pelotas**: una blanca mediana, una amarilla grande y una naranja chica, cada una con su propia velocidad.
- Cada jugador empieza con **5 vidas**. Si una pelota pasa de tu lado perdés una vida y tu puntaje baja 1; si pasa del lado de la CPU, ella pierde una vida y su puntaje baja 1. La pelota que se perdió vuelve a salir desde el centro en una dirección al azar.
- Cada vez que una pelota rebota en una pala, esa pala suma **1 punto** (Puntaje A para el jugador, Puntaje B para la CPU).
- Las pelotas también chocan entre sí e intercambian sus velocidades.
- Según en qué tercio de la pala pega la pelota (arriba, centro o abajo), cambia su dirección vertical.

### Niveles

- Si la CPU se queda sin vidas, se pasa al **siguiente nivel**: las vidas se restablecen a 5 y aparece un cartel "NIVEL X".
- La velocidad de las pelotas aumenta 25 % por nivel (nivel 1 = x1.00, nivel 10 = x3.25) y la CPU también se mueve más rápido.
- Si el jugador se queda sin vidas, es **Game Over**. Si supera el nivel 10, es **Victoria**.

## Archivos que genera

Todos son binarios de registros de tamaño fijo (módulo `struct`):

| Archivo | Contenido |
|---------|-----------|
| `usuarios.dat` | Código de usuario, nombre y apellido, usuario y clave |
| `contador_partidas.dat` | Contador general con el número de la última partida |
| `detalle_partidas.dat` | Una fila por partida: usuario, número de partida, puntaje A, puntaje B, fecha y nivel alcanzado |
| `detalle_colisiones.dat` | Cada colisión con una pala o pelota perdida: usuario, partida, fecha, coordenadas X/Y y observación |

La partida se guarda al terminar (Game Over o Victoria), y también si se sale con ESC o se cierra la ventana.

## Informes

- **Informe 1 – Movimientos por usuario y partida:** lista todas las colisiones de una partida con fecha, coordenadas y observación, y el total.
- **Informe 2 – Ranking por usuario:** todas las partidas de un usuario con sus puntajes, totales, la mejor y la peor partida.
- **Informe 3 – Matriz de colisiones (Pala × Pelota):** matriz de 2 palas por 3 pelotas con la cantidad de rebotes de cada combinación y sus totales.

## Estructura del código

- `ObjetoJuego`: clase base con nombre, posición y color.
- `Pala` y `Pelota`: clases hijas que heredan de `ObjetoJuego` y saben moverse y dibujarse.
- `Texto`: clase auxiliar para dibujar texto en pantalla.
- Funciones de archivos binarios: leer, agregar y saltar a un registro con `seek`.
- `jugar()`: bucle principal con los estados transición, jugando, game over y victoria.
- Menús de usuarios e informes por consola.
