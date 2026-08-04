# VideoScribe

[English](README.md) · **Español**

**Convierte un video en un documento escrito, con marcas de tiempo, que puedes leer, buscar y verificar.**

Tienes un video. Lo necesitas por escrito. VideoScribe toma un archivo de video y
te devuelve una transcripción, con la marca de tiempo en cada línea y una etiqueta
para cada persona que habla. También puede redactar un relato de lo que muestra la
cámara: qué trae puesta la gente, qué dice un gafete o un letrero, qué documento
cambia de manos, y en qué momento. Cada afirmación lleva su minuto, así que puedes
abrir el video en ese segundo y confirmarlo tú mismo.

Corre en tu propia computadora. La transcripción no necesita internet ni cuenta de
ningún tipo.

> **Esto es una ayuda para redactar, no una transcripción certificada.** El
> reconocimiento de voz se equivoca, sobre todo con nombres y cifras. Lee el
> resultado y verifícalo contra la grabación antes de usarlo para algo que importe.

---

## Qué hace

- Saca el sonido del video como un **MP3** que puedes reproducir donde sea.
- Escribe una **transcripción** que etiqueta cada voz como `Persona1`, `Persona2`,
  `Persona3`, y marca cada intervención con su minuto en formato `[HH:MM:SS]`.
- Genera **subtítulos SRT** que abren en cualquier reproductor.
- Opcionalmente redacta un **relato cronológico del video**. Una IA lee fotogramas
  del video y combina lo que ve con lo que se dijo, así el texto legible en
  uniformes, letreros y papeles queda en el registro escrito.
- Deja todo en una carpeta por video, con una nota en lenguaje llano que explica
  qué es cada archivo.
- **Te avisa cuando la separación de voces no es confiable**, en vez de adivinar
  en silencio.
- Funciona en Windows, macOS y Linux. Incluye instaladores.

## Qué no es

No es una transcripción certificada ni sustituye a un perito o a un secretario de
acuerdos. La separación de personas puede partir una sola voz en dos cuando la
grabación tiene ruido. Verifica el resultado contra el video antes de presentarlo,
citarlo o usarlo en cualquier procedimiento formal.

---

## Cómo empezar

### 1. Instalar

| Tu computadora | Qué hacer |
|---|---|
| **Windows** | Doble clic en **`init.cmd`** |
| **macOS / Linux** | Abre una terminal en esta carpeta y corre **`./init.sh`** |

Lo primero que pregunta es el idioma. Después revisa qué tienes ya instalado e
instala solo lo que falta: Python, ffmpeg y unos paquetes. Tarda unos minutos la
primera vez y va diciendo qué hace en cada paso.

### 2. Pon tus videos en la carpeta `inbox`

Cópialos o arrástralos ahí. Formatos aceptados: mp4, mkv, avi, mov, wmv, flv,
webm, m4v, mpg, mpeg, ts, 3gp.

### 3. Ejecutar

| Tu computadora | Qué hacer |
|---|---|
| **Windows** | Doble clic en **`run.cmd`** |
| **macOS / Linux** | Corre **`./run.sh`** |

Aparece un menú:

```
 QUE QUIERES HACER?
======================================================================
  1) Solo transcripcion         audio a texto, con quien dijo que
  2) Transcripcion + video      ademas describe lo que se ve en pantalla
  3) Revisar mi computadora     que esta instalado, que modelo le queda
  4) Idioma                     actualmente: Espanol (Spanish)
  5) Salir
```

Elige `1` o `2`. El programa te muestra qué puede con tu computadora, te deja
escoger qué tan precisa quieres la transcripción, te dice cuánto va a tardar, y
pregunta antes de empezar.

### 4. Recoger los resultados

Todo queda en `output/<nombre de tu video>/`:

| Archivo | Qué es |
|---|---|
| `00_READ_ME_FIRST.txt` | Guía en lenguaje llano de esta carpeta |
| `01_audio.mp3` | El sonido del video, solo |
| `02_transcript.txt` | Quién dijo qué, con el minuto de cada intervención |
| `03_subtitles.srt` | El mismo texto como subtítulos |
| `04_narrative.txt` | El relato escrito del video *(solo opción 2)* |
| `05_narrative_by_section.md` | El mismo relato, dividido en tramos cortos |
| `data/` | Archivos de máquina; consérvalos para rehacer un paso después |
| `work/` | Temporales; se pueden borrar |

---

## Cómo se ve el resultado

**`02_transcript.txt`**

```
[00:12:00] Persona1:
    ...no tienen por qué cobrarle, le tienen que cobrar a partir de que
    muestre su recibo, es lo que se les está pidiendo ahorita.

[00:12:16] Persona2:
    Nada más deben el 25, paguen el 25.
```

**`04_narrative.txt`** — esta es la parte que lo vuelve más que una transcripción:

> Frente al mural aparece sentada una mujer de cabello corto castaño con chamarra
> rosa palo sobre un chaleco vino. El bordado se alcanza a leer parcialmente como
> "...Reyes Toral", "...partamento De Mercados" y "H. AYUNTAMIENTO DE CHIMALHUACÁN
> 2022-2024" `[00:12:40]`. En `[00:08:40]` se ve un papel con anotaciones
> manuscritas que aparentemente muestran cifras como "$3900", coincidiendo con la
> conversación sobre montos.

Fíjate en lo que hace: cita el texto que sí alcanza a leer, dice "parcialmente" y
"aparentemente" donde no está seguro, y pone el minuto de cada observación para
que puedas comprobarla.

---

## Elegir qué tan precisa quieres la transcripción

Los modelos más grandes se equivocan menos y tardan más. Corre esto para ver los
tiempos medidos en *tu* computadora:

```
python videoscribe.py models
```

Referencia aproximada para **una hora de video en una laptop de 16 núcleos sin
tarjeta gráfica**:

| Modelo | Tiempo | Descarga | Cuándo usarlo |
|---|---|---|---|
| `tiny` | ~6 min | 75 MB | Un vistazo rápido para ver si el audio sirve |
| `base` | ~10 min | 145 MB | Todavía tosco |
| `small` | ~22 min | 480 MB | **Por defecto.** Buen equilibrio |
| `medium` | ~58 min | 1.5 GB | Claramente mejor con nombres y cifras |
| `large-v3` | ~3 horas | 3.1 GB | Lo mejor que hay; pesado sin tarjeta gráfica |

Una tarjeta gráfica lo hace varias veces más rápido. VideoScribe la detecta sola y
te recomienda un modelo más grande cuando tu equipo aguanta.

---

## Si las personas salen mal

Esta es la parte más débil, y te avisa cuando no está segura:

```
! Las voces no se separaron con claridad (mejor indice 1.22, donde 1.00
  significa que no hay estructura). Toma las etiquetas de persona como una
  guia aproximada.
```

Se arregla rápido. Si sabes cuántas personas hablan, díselo:

```
python videoscribe.py run --speakers 2 --resume
```

`--resume` reaprovecha la transcripción que ya se hizo, así que esto tarda
segundos en vez de repetir todo.

**Por qué es limitado:** las personas se separan con rasgos acústicos (timbre y
tono de voz) más agrupamiento, escrito en NumPy. Por eso la instalación es un solo
`pip install`, sin cuenta ni licencia que aceptar. Es genuinamente más débil que un
modelo neuronal entrenado, y sufre cuando varias voces parecidas hablan en un lugar
ruidoso. El detalle está en [`docs/ACCURACY.md`](docs/ACCURACY.md).

---

## Describir lo que se ve en pantalla

La transcripción no necesita nada más que tu computadora. La **descripción visual**
sí necesita un modelo que vea imágenes. Tienes cuatro opciones, y cualquiera sirve:

| Opción | Qué necesitas | Costo |
|---|---|---|
| **CLI de Claude Code** | Instalarlo desde [claude.com/claude-code](https://claude.com/claude-code) y entrar una vez | Incluido en una suscripción de Claude |
| **API de Anthropic** | `ANTHROPIC_API_KEY` en tu `.env` | Se paga por uso |
| **API de OpenAI** | `OPENAI_API_KEY` en tu `.env` | Se paga por uso |
| **Google Gemini** | `GEMINI_API_KEY` en tu `.env` | Tiene capa gratuita |

VideoScribe encuentra la que tengas y la usa. Revisa con
`python videoscribe.py doctor`.

> **Nota de privacidad.** La transcripción nunca sale de tu computadora. La
> descripción visual sí envía fotogramas del video al proveedor que elijas. Si el
> material no debe salir de tu equipo, usa la opción 1 con solo transcripción.

### Costo y detalle

Un fotograma cada 10 segundos es lo predeterminado. Para un video de 50 minutos son
unos 300 fotogramas, del orden de 600,000 tokens de entrada. Para reducirlo a la
mitad:

```
python videoscribe.py run --describe --frame-interval 20
```

---

## Ajustes

Tres lugares, cada uno le gana al anterior:

1. **`config.json`** — los valores compartidos. Edítalo para cambiarlos para todos
   los que usen esta copia.
2. **`.env`** — tu propia máquina. Copia `.env.example` a `.env` y edítalo. No se
   sube al control de versiones, así que aquí van las claves de API.
3. **Línea de comandos** — le gana a los dos. `--model medium`, `--speakers 2`, etc.

El idioma se ajusta desde la opción 4 del menú y se guarda solo en `.env`.

---

## Línea de comandos

El menú cubre lo común. Para todo lo demás:

```bash
python videoscribe.py                       # el menu
python videoscribe.py run                   # todo lo que este en inbox/
python videoscribe.py run --describe        # ademas describir la imagen
python videoscribe.py run --file charla.mp4 --model medium
python videoscribe.py run --speakers 2 --resume
python videoscribe.py run --start 00:12:00 --duration 00:03:00   # una muestra
python videoscribe.py doctor                # que esta instalado, que aguanta
python videoscribe.py models                # modelos con tiempos de tu equipo
python videoscribe.py doctor --ui-language en    # forzar el idioma
```

Sacar primero una muestra de tres minutos con `--start` y `--duration` es la forma
más barata de comprobar que el idioma y la calidad del audio son suficientes antes
de comprometerte a un proceso largo.

### PowerShell

Quien prefiera PowerShell en Windows tiene envolturas nativas con autocompletado:

```powershell
.\powershell\Transcribe.ps1 -Model medium -Speakers 2
.\powershell\Narrate.ps1 -Resume
Get-ChildItem C:\casos\*.mp4 | .\powershell\Transcribe.ps1
```

Llaman al mismo motor, así que las dos interfaces siempre coinciden.

---

## Para quién es

Cualquiera que necesite un video por escrito, y necesite poder señalar el momento
exacto en que se dijo algo:

- **Abogados** — declaraciones, audiencias, confrontaciones grabadas, videos de
  cámara corporal
- **Periodistas e investigadores** — entrevistas, conferencias, material de fuente
- **Peritos de seguros y de recursos humanos** — declaraciones e incidentes grabados
- **Investigación académica** — entrevistas cualitativas y grabaciones de campo
- **Accesibilidad** — subtítulos y descripción de lo que ocurre en pantalla

---

## Preguntas frecuentes

### ¿Cómo transcribo un video a texto gratis?

Corre el instalador de tu sistema, pon el video en `inbox/` y ejecútalo. La
transcripción, el MP3 y los subtítulos quedan en `output/<nombre del video>/`. La
herramienta es gratuita y de código abierto, y transcribir no cuesta nada porque
ocurre en tu propia computadora.

### ¿Puedo transcribir sin subir el video a la nube?

Sí, para la transcripción. El reconocimiento de voz corre localmente en tu CPU o
GPU. Después de descargar el modelo una vez, no necesita internet ni cuenta. La
excepción es la descripción visual, que sí envía fotogramas al modelo de imagen que
configures.

### ¿Cómo obtengo una transcripción que muestre quién habla?

VideoScribe lo hace solo, etiquetando las voces como `Persona1`, `Persona2`, en el
orden en que aparecen. Si ya sabes cuántas personas hay en la grabación, díselo:
`--speakers 3` es bastante más confiable que la detección automática.

### ¿Qué tan precisa es la identificación de personas?

Limitada, y honesta al respecto. Puede partir la voz de una persona en dos cuando
hay ruido, y te avisa en el resultado cuando las voces no se separaron con
claridad. Ver [`docs/ACCURACY.md`](docs/ACCURACY.md).

### ¿La IA puede describir lo que pasa en el video, no solo lo que se dice?

Sí, como paso opcional. Un modelo de imagen lee fotogramas y combina lo que ve
—ropa, gafetes, letreros, documentos, texto legible— con la transcripción. Cada
afirmación lleva su minuto para que puedas comprobarla.

### ¿Cuánto tarda en transcribir una hora de video?

En una medición real, 50 minutos de video tardaron unos 21 minutos en un CPU de 16
núcleos sin tarjeta gráfica, con el modelo `small`. Corre
`python videoscribe.py models` para un estimado de tu propio equipo.

### ¿Necesito tarjeta gráfica?

No. Los valores por defecto están pensados para una máquina solo con CPU. Una
tarjeta gráfica lo hace más rápido y te permite usar un modelo más grande sin
problema.

### ¿Una transcripción hecha por IA sirve como prueba en juicio?

Trátala como una ayuda para redactar. VideoScribe no es una transcripción
certificada y no afirma nada sobre su admisibilidad. Una persona debe verificar el
resultado contra la grabación antes de usarlo en cualquier procedimiento formal. El
minuto en cada línea existe justo para que esa verificación sea rápida.

---

## Cómo funciona

```
archivo de video
    |
    +-- ffmpeg ------------> MP3 (para ti) + WAV 16 kHz (para los modelos)
    |
    +-- faster-whisper ----> segmentos de texto con tiempos
    |
    +-- MFCC + tono -------> rasgos por segmento
    |     + agrupamiento     -> Persona1, Persona2, ...
    |
    +-- ffmpeg ------------> un fotograma cada N segundos       (opcional)
    |
    +-- modelo de imagen --> un parrafo por cada dos minutos    (opcional)
    |
    +-- modelo de imagen --> un relato continuo                 (opcional)
```

Dos decisiones de diseño que conviene conocer:

**Los minutos se truncan, nunca se redondean.** En el segundo 40.7 la etiqueta es
`00:00:40`, no `00:00:41`, porque el 41 podría ser ya la siguiente frase. Todos los
minutos se refieren al video original, aunque solo se haya procesado un tramo.

**Los minutos inventados se eliminan.** Los modelos de lenguaje estiman los tiempos
cuando se les pide citarlos. Cada `[HH:MM:SS]` que escribe el modelo de imagen se
compara contra los tiempos reales de fotogramas y transcripción de ese tramo, y se
borra si no coincide. Un minuto equivocado es peor que ninguno: manda al lector al
punto incorrecto.

---

## Requisitos

- Python 3.9 o más nuevo
- ffmpeg
- Unos 2 GB de disco para el modelo predeterminado
- Solo para la descripción visual: una de las cuatro opciones de modelo de imagen

Los instaladores se encargan de todo esto.

## Documentación

- [`docs/ACCURACY.md`](docs/ACCURACY.md) — qué creer, qué verificar, y por qué
- [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) — todos los ajustes explicados
- [`tests/README.md`](tests/README.md) — cómo funcionan las pruebas en contenedor
- [`CLAUDE.md`](CLAUDE.md) — notas para asistentes de IA que trabajen en este repo

## Pruebas

El arranque y el comportamiento del menú se prueban en Linux dentro de un
contenedor, para que el resultado no dependa de la máquina donde se corren:

```bash
bash tests/run_container_tests.sh      # necesita podman, o ENGINE=docker
```

## Licencia

MIT. Ver [`LICENSE`](LICENSE).
