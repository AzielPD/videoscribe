# VideoScribe — transcribe video y audio a texto con marcas de tiempo, sin internet

[English](README.md) · **Español**

**Convierte un video o una grabación de audio en una transcripción buscable y con
marcas de tiempo — quién dijo qué, en qué segundo — enteramente en tu propia
computadora. Sin cuenta, sin subir nada, sin nube.**

Tienes una grabación. La necesitas por escrito. VideoScribe toma un archivo de
video o de audio y te devuelve una transcripción, con la marca de tiempo en cada
línea y una etiqueta para cada persona que habla. También puede redactar un relato
de lo que muestra la cámara: qué trae puesta la gente, qué dice un gafete o un
letrero, qué documento cambia de manos, y en qué momento. Cada afirmación lleva su
marca de tiempo, así que puedes abrir la grabación en ese segundo y confirmarlo tú
mismo.

El reconocimiento de voz corre **sin conexión (offline)** en tu propio procesador o
tarjeta gráfica, con Whisper de OpenAI a través de
[faster-whisper](https://github.com/SYSTRAN/faster-whisper). Después de descargar
el modelo una vez, la transcripción no necesita internet ni cuenta de ningún tipo.

> **Esto es una ayuda para redactar, no una transcripción certificada.** El
> reconocimiento de voz se equivoca, sobre todo con nombres y cifras. Lee el
> resultado y verifícalo contra la grabación antes de usarlo para algo que importe.

---

## Qué hace

- Acepta **video o audio**: `.mp4`, `.mkv`, `.mov`, `.avi`, `.webm` y los demás,
  más `.mp3`, `.wav`, `.m4a`, `.flac` y otros formatos de audio. Una grabación de
  Zoom, Teams o Meet funciona tal como viene.
- Saca el sonido como un **MP3** que puedes reproducir donde sea.
- Escribe una **transcripción** que etiqueta cada voz como `Persona1`, `Persona2`,
  `Persona3`, y marca cada intervención con su marca de tiempo en formato
  `[HH:MM:SS]`.
- Genera **subtítulos SRT** que abren en cualquier reproductor.
- Funciona **sin conexión (offline)** después de la primera descarga del modelo —
  sin internet, sin cuenta, sin subir nada.
- Opcionalmente redacta un **relato cronológico del video**. Una IA lee fotogramas
  del video y combina lo que ve con lo que se dijo, así el texto legible en
  uniformes, letreros y papeles queda en el registro escrito.
- Deja todo en una carpeta por grabación, con una nota en lenguaje llano que
  explica qué es cada archivo.
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

### 2. Pon tus grabaciones en la carpeta `inbox`

Cópialas o arrástralas ahí.

- **Video:** mp4, mkv, avi, mov, wmv, flv, webm, m4v, mpg, mpeg, ts, 3gp
- **Audio:** mp3, wav, m4a, aac, ogg, opus, flac, wma, aiff

Los archivos de audio funcionan igual que los de video, salvo por la descripción
de lo que se ve en pantalla.

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

Si no hay ningún modelo de imagen configurado, la opción 2 aparece como *no
disponible* y al elegirla te explica qué falta. La transcripción nunca depende de
uno.

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

Los ejemplos de abajo son inventados, no material de un caso real.

**`02_transcript.txt`**

```
[00:03:48] Persona1:
    En el recibo me aparecen dos mil pesos de recargo y en la ventanilla
    me dijeron otra cifra; quiero que me expliquen de dónde sale.

[00:04:05] Persona2:
    El recargo se calcula por trimestre vencido, señora. Le imprimo el
    desglose y si está mal, aquí mismo se lo corregimos.
```

**`04_narrative.txt`** — esta es la parte que lo vuelve más que una transcripción:

> Frente a la ventanilla aparece sentada una persona con playera blanca bajo un
> chaleco verde olivo. El bordado se alcanza a leer parcialmente como
> "...ano de Tal", "...ección De Parques" y "H. AYUNTAMIENTO DE VILLA EJEMPLO
> 2018-2021" `[00:04:20]`. En `[00:06:05]` se ve un papel con anotaciones
> manuscritas que aparentemente muestran cifras como "$1,780", coincidiendo con la
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

**En un CPU de varios núcleos la grabación se parte y se transcribe en paralelo.** El
propio hilado de whisper deja de ayudar pasados unos cuatro núcleos, así que el resto
se quedaría sin hacer nada. Los cortes caen en silencios, nunca a media palabra, y una
grabación sin silencios aprovechables se transcribe de una pieza. Medido sobre 8
minutos de audio con 16 núcleos: 2:44 en una parte, 1:41 en dos, 1:37 en cuatro. Pasa
solo; pon `transcription.workers` en 1 para desactivarlo.

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

**Por qué es limitado:** la diarización de hablantes aquí usa rasgos acústicos
(timbre y tono de voz) más agrupamiento, escrito en NumPy. Por eso la instalación es un solo
`pip install`, sin cuenta ni licencia que aceptar. Es genuinamente más débil que un
modelo neuronal entrenado, y sufre cuando varias voces parecidas hablan en un lugar
ruidoso. El detalle está en [`docs/ACCURACY.es.md`](docs/ACCURACY.es.md).

---

## Describir lo que se ve en pantalla

La transcripción no necesita nada más que tu computadora. La **descripción visual**
sí necesita un modelo que vea imágenes. Cualquiera de estas sirve, y basta con una.

### Qué necesita cada opción

| Opción | Cómo conectarla | Costo |
|---|---|---|
| **Google Gemini** | Entra a [aistudio.google.com/apikey](https://aistudio.google.com/apikey) con tu cuenta de Google de siempre, botón *Create API key*, y la pegas | Tiene capa gratuita |
| **CLI de Claude Code** | Instálalo desde [claude.com/claude-code](https://claude.com/claude-code), corre `claude` una vez y entra | Incluido en una suscripción de Claude |
| **API de Anthropic** | Crea una clave en [console.anthropic.com](https://console.anthropic.com/settings/keys) | Se paga por uso, la cuenta necesita saldo |
| **API de OpenAI** | Crea una clave en [platform.openai.com](https://platform.openai.com/api-keys) | Se paga por uso, la cuenta necesita saldo |
| **Un modelo en tu propia computadora** | Instala [Ollama](https://ollama.com); VideoScribe se ofrece a descargar el modelo | Gratis, y nada sale de la máquina |

**No tienes que editar ningún archivo.** Corre `python videoscribe.py`, elige la
opción con descripción, y el menú te pregunta qué proveedor tienes, te pide la clave
y la guarda en `.env` por ti. La clave se escribe oculta, y `.env` nunca se sube al
control de versiones.

Si prefieres hacerlo a mano, basta una línea en `.env`:

```
GEMINI_API_KEY=...
```

Revisa qué encontró con `python videoscribe.py doctor`.

### Si no tienes ninguna

**Empieza con Gemini.** Tiene capa gratuita, la clave toma como un minuto, y no
necesita más que la cuenta de Google que ya tienes. **No hace falta una suscripción
de Claude** para usar esta herramienta: la opción de Claude Code está ahí para quien
ya la tenga.

### ¿Se puede entrar con la cuenta de Google en vez de pegar una clave?

En la práctica eso es justo lo que ya es la opción de Gemini: entras con tu cuenta de
Google en AI Studio y presionas un botón. Lo que te devuelve se llama clave de API en
vez de sesión, pero el resto del trámite es igual, y la capa gratuita no pide datos
de pago.

Un OAuth completo no vale la pena aquí. El camino de OAuth de Google para modelos es
Vertex AI, que exige un proyecto de Google Cloud, una cuenta de facturación y la
herramienta `gcloud`: estrictamente más trabajo que pegar una clave. Y para un
programa que corre en tu propia computadora, OAuth significa meter un secreto de
cliente dentro de un repositorio público y levantar un servidor web pequeño para
recibir la redirección: más cosas que se pueden romper, para el mismo requisito de
tener una cuenta.

**Hugging Face** no está soportado hoy. También sería un token pegado en `.env` y no
un inicio de sesión, así que tampoco te ahorraría el paso que quieres evitar. Es una
opción razonable de agregar si quieres un proveedor gratuito que no sea Google:
pídelo.

### Sobre la opción local

Es la única que no envía nada por internet, lo que puede decidir el asunto con
material confidencial. Ten clara la contrapartida, medida en una máquina de 16
núcleos sin tarjeta gráfica:

- **Velocidad.** Unos 80 segundos por fotograma, que con el valor predeterminado de
  un fotograma cada 10 segundos son aproximadamente **8 veces la duración de la
  grabación**. Un video de una hora toma casi un día. Una tarjeta gráfica es del
  orden de diez veces más rápida.
- **Letra chica.** Leyó bien el nombre del municipio bordado en un uniforme, pero
  parafraseó la línea de arriba y ni intentó el nombre de la persona debajo.
- **Marcas de tiempo.** En las pruebas no escribió **ninguna**, aunque el prompt se
  las pide. Como el sentido del relato es poder comprobar una afirmación contra el
  video, ésta es la razón por la que no se ofrece como opción predeterminada en una
  computadora sin tarjeta gráfica.

Tanto el menú como `doctor` te dicen cuál de estos casos aplica a tu computadora
antes de que te comprometas a nada.

> **Nota de privacidad.** La transcripción nunca sale de tu computadora, elijas la
> opción que elijas. La descripción visual sí envía fotogramas del video al proveedor
> que elijas. Si el material no debe salir de tu equipo, usa el modelo local, o pide
> solo transcripción y deja la descripción apagada.

### Costo y detalle

Un fotograma cada 10 segundos es lo predeterminado. Para un video de 50 minutos son
unos 300 fotogramas, del orden de 600,000 tokens de entrada. Para reducirlo a la
mitad:

```
python videoscribe.py run --describe --frame-interval 20
```

Con el modelo local no necesitas ajustar nada: calcula cuántos fotogramas caben en su
ventana de contexto y aguanta tu procesador, acorta los tramos para que quepan, y te
avisa en pantalla que lo hizo.

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

### Para quién funciona bien, y cuáles son sus limitaciones

La mayoría de las herramientas solo te cuentan la primera mitad. Aquí van las dos,
para que decidas antes de gastar una hora transcribiendo.

**Le sirve bien.** A un despacho pequeño o mediano, con equipo de oficina normal,
que trabaja en español o inglés y necesita una transcripción citable de una
audiencia, una declaración o una reunión — y para quien importa que la grabación
nunca salga de la computadora. Ese es el caso central y está cubierto con solidez.

**Le sirve a medias.** A quien necesita el relato escrito de lo que se ve en
pantalla. Salvo que la máquina tenga tarjeta gráfica, esa parte depende de un
proveedor externo. La transcripción nunca depende de nadie.

**Le sirve mal, y hay que decirlo claro:**

- **A quien necesite saber *con certeza* quién habló.** Aquí la separación de
  hablantes agrupa voces por MFCC y tono, no por huellas neuronales de voz. Es una
  decisión deliberada para que la instalación siga siendo un solo `pip install`,
  sin cuenta y sin licencia que aceptar. El programa reporta un índice de separación en cada
  corrida y te advierte cuando baja de 1.25, donde 1.00 significa que el audio no
  tenía ninguna división natural y las etiquetas de persona son casi arbitrarias.
  Con varias voces parecidas en una sala ruidosa, tómalas como guía aproximada y
  verifícalas. La herramienta es honesta al respecto; aun así es lo más débil que
  hace. Ve [`docs/ACCURACY.es.md`](docs/ACCURACY.es.md).
- **A quien no vaya a abrir jamás una terminal.** Hoy eso significa hacer doble
  clic en `run.cmd` y teclear un número leyendo una tabla de ancho fijo. Funciona,
  y gente que nunca ha usado la línea de comandos sí lo logra, pero es la arista
  más áspera de todo el producto.

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

### ¿Cómo transcribo un audio a texto, no solo un video?

Igual que un video. Deja un `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.opus`,
`.aac`, `.wma` o `.aiff` en `inbox/`, o apunta directo con `--file`. Todo funciona
igual: transcripción, etiquetas de persona, marcas de tiempo y subtítulos. Lo único
que no aplica es la descripción visual, porque no hay imagen; el programa lo dice y
sigue adelante.

### ¿Sirve para transcribir una audiencia o una declaración?

Es para lo que se diseñó. La razón de ser de la herramienta es que puedas citar una
frase y señalar el segundo exacto en que se dijo, para que cualquiera lo compruebe
tecleando esa marca en un reproductor. Lee antes
[Para quién funciona bien, y cuáles son sus limitaciones](#para-quién-funciona-bien-y-cuáles-son-sus-limitaciones):
la separación de personas es lo más débil, y en una sala con varias voces parecidas
conviene indicar cuántas personas hay con `--speakers`.

### ¿Puedo transcribir una grabación de Zoom, Teams o Google Meet?

Sí, tal como viene. Esas aplicaciones guardan video `.mp4` o audio `.m4a`, y ambos
se reconocen sin convertir nada. Es la ruta habitual para declaraciones a distancia,
entrevistas grabadas y juntas de recursos humanos.

### ¿Funciona con el español de México y otros acentos?

Sí. El modelo de voz se entrenó con español de muchas regiones y no distingue entre
variantes. Lo que sí cambia el resultado es el tamaño del modelo: `small` se equivoca
con nombres propios y cifras bastante más que `medium`. Si el material tiene nombres,
domicilios o cantidades que importan, usa el modelo más grande que aguante tu
computadora y verifica esas partes contra la grabación.

### ¿Funciona sin conexión a internet?

Sí, para la transcripción, que es el uso principal. El modelo de voz se descarga una
vez —entre 75 MB y 3.1 GB según cuál elijas— y después todo corre en tu máquina sin
conexión y sin cuenta. Solo la descripción opcional de lo que se ve en pantalla
necesita internet.

### ¿Puedo transcribir varias grabaciones a la vez?

Sí. Ponlas todas en `inbox/` y ejecuta una vez; cada una recibe su propia carpeta en
`output/`. Además, en una computadora con varios núcleos cada grabación se reparte
internamente entre trabajadores, que es por lo que una máquina de 16 núcleos es
mucho más rápida que una de 4.

### ¿Cómo paso la transcripción a Word?

Abre `02_transcript.txt` directamente en Word — es texto plano UTF-8 y Word lo lee
sin convertir nada. Usa *Archivo → Guardar como* si quieres un `.docx`. El archivo
de subtítulos `03_subtitles.srt` también es texto plano y se abre igual.

### ¿Cómo obtengo una transcripción que muestre quién habla?

VideoScribe lo hace solo, etiquetando las voces como `Persona1`, `Persona2`, en el
orden en que aparecen. Si ya sabes cuántas personas hay en la grabación, díselo:
`--speakers 3` es bastante más confiable que la detección automática.

### ¿Qué tan precisa es la identificación de personas?

Limitada, y honesta al respecto. Puede partir la voz de una persona en dos cuando
hay ruido, y te avisa en el resultado cuando las voces no se separaron con
claridad. Ver [`docs/ACCURACY.es.md`](docs/ACCURACY.es.md).

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

### Lo mínimo, y qué te da

| Necesitas | Y obtienes |
|---|---|
| Python 3.9 o más nuevo | |
| ffmpeg — si falta, el programa se ofrece a instalarlo, incluso con una copia portable que no necesita permisos de administrador | **Una transcripción** con quién dijo qué y una marca de tiempo en cada línea |
| Unos 2 GB de disco para el modelo predeterminado | **Subtítulos** en un archivo `.srt` |
| | Un `.json` legible por máquina con lo mismo |

**Esa es toda la lista.** Ninguna cuenta, ninguna clave de API, ninguna tarjeta, y
ninguna conexión a internet después de que la primera corrida descargue el modelo.
Esto es lo que la mayoría necesita, y es la parte que nunca envía tu grabación a
ningún lado.

### Para además describir lo que se ve en pantalla

Esta parte sí necesita un modelo que pueda ver imágenes, porque nada en tu
computadora puede leer un fotograma por su cuenta. Cualquiera **una** de estas:

- **Una clave de Google Gemini** — capa gratuita, solo necesita la cuenta de Google
  que ya tienes. Lo más rápido si no tienes ninguna de las otras.
- **El comando `claude`**, desde [claude.com/claude-code](https://claude.com/claude-code),
  con sesión iniciada una vez. Usa una suscripción de Claude que ya pagas. (El back
  end ejecuta el comando `claude`, así que tiene que estar en tu PATH — instalar la
  herramienta de línea de comandos es lo que lo pone ahí.)
- **Una clave de Anthropic o de OpenAI**, si ya tienes una. Ambas se pagan por uso y
  la cuenta necesita saldo.
- **Ollama y una tarjeta gráfica**, si el material no debe salir de la máquina para
  nada. Lee primero [Sobre la opción local](#sobre-la-opción-local): sin tarjeta
  gráfica toma unas ocho veces la duración de la grabación y no escribe marcas de
  tiempo.

[Cómo conectar cada una](#qué-necesita-cada-opción) es una tabla más arriba.

### Si no configuras ninguna

No se rompe nada ni se esconde nada. El menú muestra la opción de descripción
marcada como *no disponible*, y si la eliges te explica qué falta y se ofrece a
configurar una. Las corridas producen la transcripción y los subtítulos con
normalidad, y `python videoscribe.py run --describe` avisa que se omitió la
descripción y sigue adelante en vez de fallar.

Los instaladores se encargan de todo lo de la lista mínima.

## Documentación

- [`docs/ACCURACY.es.md`](docs/ACCURACY.es.md) — qué creer, qué verificar, y por qué
- [`docs/CONFIGURATION.es.md`](docs/CONFIGURATION.es.md) — todos los ajustes explicados
- [`tests/README.md`](tests/README.md) — cómo funcionan las pruebas en contenedor
- [`CLAUDE.md`](CLAUDE.md) — notas para asistentes de IA que trabajen en este repo

## Pruebas y revisiones

Todo corre con un solo comando:

```bash
pip install -r requirements-dev.txt
python scripts/check.py
```

Eso corre cuatro cosas, y reporta las cuatro aunque una anterior falle:

| Revisión | Qué cubre |
|---|---|
| **pruebas unitarias** | 128 pruebas sobre las reglas que no se pueden romper: las marcas de tiempo truncan en vez de redondear, cada tiempo se refiere al video original, las marcas inventadas se eliminan, la precedencia de ajustes, y los límites del modelo local |
| **calidad de código** | `ruff` — nombres sin usar, orden de imports, errores probables, estilo |
| **seguridad (código)** | `bandit` — extracción de archivos comprimidos, esquemas de URL, uso de subprocesos |
| **seguridad (dependencias)** | `pip-audit` — vulnerabilidades conocidas en lo que instalamos |

Corre un solo grupo con `python scripts/check.py tests`, `quality` o `security`.

Además, el arranque y el comportamiento del menú se prueban en Linux dentro de un
contenedor, para que el resultado no dependa de la máquina donde se corren:

```bash
bash tests/run_container_tests.sh      # necesita podman, o ENGINE=docker
```

## Licencia

MIT. Ver [`LICENSE`](LICENSE).
