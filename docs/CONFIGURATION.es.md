# Configuración

[English](CONFIGURATION.md) · **Español**

Cada ajuste se puede cambiar en tres lugares. Cada uno le gana al anterior:

```
valores por defecto  <  config.json  <  .env  <  linea de comandos
   (del codigo)        (compartido)    (tuyo)     (esta corrida)
```

- **`config.json`** — los valores compartidos. Edítalo para cambiar el
  comportamiento de todos los que usen esta copia de la herramienta. Sí se sube al
  control de versiones.
- **`.env`** — tu propia máquina. Copia `.env.example` a `.env` y edítalo. *No* se
  sube al control de versiones, así que aquí van las claves de API y las rutas
  propias de tu equipo.
- **Línea de comandos** — le gana a todo, para una sola corrida.

---

## Transcripción

| config.json | .env | Línea de comandos | Por defecto |
|---|---|---|---|
| `transcription.model` | `VIDEOSCRIBE_MODEL` | `--model` | `small` |
| `transcription.language` | `VIDEOSCRIBE_LANGUAGE` | `--language` | `es` |
| `transcription.compute_type` | `VIDEOSCRIBE_COMPUTE_TYPE` | — | `int8` |
| `transcription.beam_size` | — | — | `5` |
| `transcription.cpu_threads` | `VIDEOSCRIBE_CPU_THREADS` | — | `0` |

**`model`** — `tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3`. Más grande
es más preciso y más lento. Corre `python videoscribe.py models` para ver los
tiempos medidos en tu computadora.

**`language`** — un código de dos letras (`es`, `en`, `pt`, `fr`) o `auto`.
**Ponerlo mal es la causa más común de un mal primer resultado.** De fábrica viene
en español; cámbialo si ese no es tu idioma. `auto` funciona, pero cuesta un poco de
precisión en grabaciones cortas.

**`compute_type`** — `int8` es lo correcto para CPU. Con tarjeta gráfica, `float16`
es más rápido y un poco más preciso.

**`cpu_threads`** — `0` significa usar todos los núcleos, hasta 16. Bájalo si
quieres que la computadora siga respondiendo mientras trabaja.

---

## Personas que hablan

| config.json | .env | Línea de comandos | Por defecto |
|---|---|---|---|
| `speakers.count` | `VIDEOSCRIBE_SPEAKERS` | `--speakers` | `0` |
| `speakers.max_count` | `VIDEOSCRIBE_MAX_SPEAKERS` | `--max-speakers` | `6` |
| `speakers.label` | `VIDEOSCRIBE_SPEAKER_LABEL` | — | *(sigue al idioma)* |

**`count`** — cuántas personas hablan. `0` le pide al programa que lo averigüe,
cosa poco confiable en grabaciones con ruido. Si sabes el número, dáselo: el
resultado es notablemente mejor. Combínalo con `--resume` para volver a etiquetar
sin volver a transcribir.

**`label`** — la palabra que va antes del número. `Person` da `Person1`, `Person2`.
Usa `Speaker` para un resultado en inglés y `Persona` para español.

Consulta [`ACCURACY.es.md`](ACCURACY.es.md) para saber qué esperar de este paso.

---

## Descripción visual

| config.json | .env | Línea de comandos | Por defecto |
|---|---|---|---|
| `narration.enabled` | `VIDEOSCRIBE_NARRATION` | `--describe` | `true` |
| `narration.frame_interval_seconds` | `VIDEOSCRIBE_FRAME_INTERVAL` | `--frame-interval` | `10` |
| `narration.window_seconds` | `VIDEOSCRIBE_WINDOW_SECONDS` | `--window` | `120` |
| `narration.max_frame_edge` | — | — | `1568` |
| `narration.vision_model` | `VIDEOSCRIBE_VISION_MODEL` | — | *(automático)* |
| `narration.synthesis_model` | `VIDEOSCRIBE_SYNTHESIS_MODEL` | — | *(automático)* |
| `narration.output_language` | `VIDEOSCRIBE_NARRATION_LANGUAGE` | — | `Spanish` |
| — | — | `--vision-backend` | `auto` |

**`frame_interval_seconds`** — un fotograma cada N segundos. Este es el control
principal del costo. A 10 segundos, un video de 50 minutos produce unos 300
fotogramas y del orden de 600,000 tokens de entrada. A 20 segundos, la mitad. Bájalo
de 10 solo cuando importen las acciones breves, como un documento que cambia de
manos.

**`window_seconds`** — cuánto video se describe por petición. Las ventanas más
grandes le dan más contexto al modelo y ahorran peticiones, pero cada petición pesa
más. 120 es un buen equilibrio.

**`max_frame_edge`** — los fotogramas se escalan para caber dentro de ese cuadrado.
1568 px es el punto a partir del cual los modelos reducen la imagen de todos modos,
así que valores más grandes desperdician disco y tiempo de subida sin agregar
detalle legible.

**`output_language`** — escrito con todas sus letras y en inglés: `Spanish`,
`English`, `Portuguese`. Controla el idioma en el que se *redacta* el relato, sin
importar el idioma que se habla en el video.

---

## Qué modelo de imagen describe el video

Usa `--vision-backend` o déjalo en `auto`, que los prueba en este orden y toma el
primero que esté configurado:

| Motor | Qué necesita |
|---|---|
| `claude-cli` | El comando `claude` instalado y con la sesión iniciada. Sin clave de API. |
| `anthropic` | `ANTHROPIC_API_KEY` en `.env` |
| `openai` | `OPENAI_API_KEY` en `.env` |
| `gemini` | `GEMINI_API_KEY` en `.env` |
| `ollama` | [Ollama](https://ollama.com) corriendo localmente. Sin cuenta, nada sale por internet, pero mas lento y peor con la letra chica. |

Revisa qué tienes disponible con `python videoscribe.py doctor`.

Nombrar un motor en lugar de dejar `auto` hace que el programa falle de forma
visible si no está configurado, en vez de usar otro en silencio.

### Agregar otro proveedor

Escribe una clase en `videoscribe/vision.py` con un método de clase
`is_available()` y un método `generate(prompt, images, model)`, y agrégala al
diccionario `BACKENDS`. Unas 30 líneas.

---

## Carpetas

| config.json | .env | Línea de comandos | Por defecto |
|---|---|---|---|
| `paths.inbox` | `VIDEOSCRIBE_INBOX` | — | `inbox` |
| `paths.output` | `VIDEOSCRIBE_OUTPUT` | `--output` | `output` |
| `paths.ffmpeg` | `VIDEOSCRIBE_FFMPEG` | — | *(se busca sola)* |

Las rutas relativas se cuentan desde la carpeta del repositorio. Las rutas absolutas
también sirven, lo cual es útil para mandar los resultados a la carpeta de un caso o
a una unidad de red.

**`ffmpeg`** — déjalo vacío y se encuentra solo: primero en el PATH, después en las
carpetas de instalación habituales. Ponlo solo si ffmpeg está en un lugar poco
común.

---

## Limpieza

| config.json | .env | Línea de comandos | Por defecto |
|---|---|---|---|
| `cleanup.keep_wav` | `VIDEOSCRIBE_KEEP_WAV` | `--keep-work` | `false` |
| `cleanup.keep_frames` | `VIDEOSCRIBE_KEEP_FRAMES` | `--keep-work` | `false` |

El WAV temporal pesa unos 2 MB por minuto de video; cada fotograma, unos 200 KB.
Los dos se borran cuando la corrida termina bien. Consérvalos mientras experimentas,
porque así `--resume` puede reaprovecharlos.

---

## Audio

| config.json | .env | Por defecto |
|---|---|---|
| `audio.mp3_bitrate` | `VIDEOSCRIBE_MP3_BITRATE` | `128k` |
| `audio.sample_rate` | — | `16000` |

**`sample_rate`** no se debe cambiar. El modelo de voz espera 16 kHz, y los rasgos
acústicos que se usan para separar a las personas lo dan por hecho en todo momento.

---

## Ejemplos resueltos

**Una muestra rápida antes de comprometerte a un proceso largo**

```bash
python videoscribe.py run --start 00:12:00 --duration 00:03:00 --model tiny
```

**Grabación en inglés, dos personas, la mayor precisión disponible**

```bash
python videoscribe.py run --language en --speakers 2 --model large-v3
```

**Volver a etiquetar a las personas sin volver a transcribir**

```bash
python videoscribe.py run --speakers 3 --resume
```

**Descripción visual a la mitad del costo normal**

```bash
python videoscribe.py run --describe --frame-interval 20
```

**Continuar después de una corrida interrumpida**

```bash
python videoscribe.py run --describe --resume
```

Los tramos que ya se escribieron se conservan; solo se vuelven a pedir los que
faltan.
