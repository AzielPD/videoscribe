"""Translations for everything the user sees on screen.

Two languages are supported: English (``en``) and Spanish (``es``).

How the language is chosen, highest priority first:

1. ``--ui-language`` on the command line
2. ``VIDEOSCRIBE_UI_LANGUAGE`` in ``.env``
3. ``ui.language`` in ``config.json``
4. The operating system's own language, if it is one we support
5. English

Adding a language means adding one more entry to every dictionary below and
listing it in :data:`LANGUAGE_NAMES`. Nothing else needs changing: the rest of
the program only ever calls :func:`t`.

Keys are dotted and grouped by where they appear, so a missing translation is
easy to trace back to the screen it belongs to.
"""

from __future__ import annotations

import locale
import os

DEFAULT_LANGUAGE = "en"

# Shown in the language picker, in each language's own words.
LANGUAGE_NAMES = {
    "en": "English",
    "es": "Espanol (Spanish)",
}

# What each interface language implies for the written output, when the user
# has not chosen otherwise. Someone reading a Spanish menu almost certainly
# wants a Spanish account of their video.
LANGUAGE_DEFAULTS = {
    "en": {
        "transcription.language": "en",
        "narration.output_language": "English",
        "speakers.label": "Speaker",
    },
    "es": {
        "transcription.language": "es",
        "narration.output_language": "Spanish",
        "speakers.label": "Persona",
    },
}

_current = DEFAULT_LANGUAGE


MESSAGES: dict[str, dict[str, str]] = {
    # --- Application framing ---------------------------------------------
    "app.tagline": {
        "en": "VIDEOSCRIBE  --  turn a video into a written, checkable document",
        "es": "VIDEOSCRIBE  --  convierte un video en un documento escrito y verificable",
    },
    "app.videos_folder": {
        "en": "Videos folder : {path}",
        "es": "Carpeta de videos    : {path}",
    },
    "app.results_folder": {
        "en": "Results folder: {path}",
        "es": "Carpeta de resultados: {path}",
    },
    "app.videos_waiting": {
        "en": "Found {count} video(s) waiting:",
        "es": "Se encontraron {count} video(s) en espera:",
    },
    "app.no_videos": {
        "en": "No videos found yet.",
        "es": "Todavia no hay videos.",
    },
    "app.copy_videos_into": {
        "en": "Copy your video files into:  {path}",
        "es": "Copia tus archivos de video en:  {path}",
    },
    "app.nothing_to_process": {
        "en": "There is nothing to process. Put a video in {path} and start again.",
        "es": "No hay nada que procesar. Pon un video en {path} y vuelve a empezar.",
    },
    "app.results_in": {
        "en": "Results in: {path}",
        "es": "Resultados en: {path}",
    },
    "app.finished": {"en": "FINISHED", "es": "TERMINADO"},
    "app.done": {
        "en": "Done. Results are in: {path}",
        "es": "Listo. Los resultados estan en: {path}",
    },
    "app.failed_count": {
        "en": "{count} video(s) failed; see the messages above.",
        "es": "{count} video(s) fallaron; revisa los mensajes de arriba.",
    },
    "app.could_not_process": {
        "en": "!! {name} could not be processed:",
        "es": "!! No se pudo procesar {name}:",
    },
    "app.please_note": {"en": "Please note:", "es": "Ten en cuenta:"},
    "app.video_n_of_m": {
        "en": "VideoScribe  --  video {position} of {total}",
        "es": "VideoScribe  --  video {position} de {total}",
    },

    # --- Prompts ----------------------------------------------------------
    "prompt.pick_number": {"en": "Pick a number", "es": "Elige un numero"},
    "prompt.answer_one_of": {
        "en": "Please answer one of: {options}",
        "es": "Responde una de estas opciones: {options}",
    },
    "prompt.cancelled": {"en": "Cancelled.", "es": "Cancelado."},
    "prompt.yes_no": {"en": "(y/n)", "es": "(s/n)"},
    "prompt.start_now": {"en": "Start now?", "es": "Empezar ahora?"},

    # --- Main menu --------------------------------------------------------
    "menu.header": {
        "en": "WHAT WOULD YOU LIKE TO DO?",
        "es": "QUE QUIERES HACER?",
    },
    "menu.option_transcript": {
        "en": "Transcript only            audio to text, with who said what",
        "es": "Solo transcripcion         audio a texto, con quien dijo que",
    },
    "menu.option_describe": {
        "en": "Transcript + description   also describe what is seen on screen",
        "es": "Transcripcion + video      ademas describe lo que se ve en pantalla",
    },
    "menu.option_check": {
        "en": "Check my computer          what is installed, which model fits",
        "es": "Revisar mi computadora     que esta instalado, que modelo le queda",
    },
    "menu.option_language": {
        "en": "Language                   currently: {language}",
        "es": "Idioma                     actualmente: {language}",
    },
    "menu.option_quit": {"en": "Quit", "es": "Salir"},

    # --- Language picker --------------------------------------------------
    "language.header": {
        "en": "SELECT LANGUAGE  /  SELECCIONA IDIOMA",
        "es": "SELECCIONA IDIOMA  /  SELECT LANGUAGE",
    },
    "language.explain": {
        "en": "This sets the language of the menus and of the documents produced.",
        "es": "Esto cambia el idioma de los menus y de los documentos que se generan.",
    },
    "language.saved": {
        "en": "Saved. Menus and output will now be in {language}.",
        "es": "Guardado. Los menus y los resultados ahora seran en {language}.",
    },
    "language.also_sets": {
        "en": "Speech language set to '{code}' and written accounts to {written}.",
        "es": "Idioma del audio ajustado a '{code}' y de los relatos a {written}.",
    },
    "language.change_later": {
        "en": "You can change this any time from the menu.",
        "es": "Puedes cambiarlo cuando quieras desde el menu.",
    },

    # --- Machine report ---------------------------------------------------
    "machine.header": {"en": "YOUR COMPUTER", "es": "TU COMPUTADORA"},
    "machine.system": {"en": "System        : {value}", "es": "Sistema        : {value}"},
    "machine.cores": {"en": "CPU cores     : {value}", "es": "Nucleos de CPU : {value}"},
    "machine.memory": {"en": "Memory        : {value} GB", "es": "Memoria        : {value} GB"},
    "machine.disk": {"en": "Free disk     : {value} GB", "es": "Disco libre    : {value} GB"},
    "machine.gpu": {
        "en": "Graphics card : {name} ({vram} GB)",
        "es": "Tarjeta grafica: {name} ({vram} GB)",
    },
    "machine.no_gpu": {
        "en": "Graphics card : none detected (the CPU will do the work)",
        "es": "Tarjeta grafica: no se detecto (el CPU hara el trabajo)",
    },
    "machine.recommended": {
        "en": "Recommended model: {model}",
        "es": "Modelo recomendado: {model}",
    },

    # --- Model recommendations -------------------------------------------
    "recommend.gpu_large": {
        "en": "Your {gpu} has enough memory to run the most accurate model at "
              "good speed.",
        "es": "Tu {gpu} tiene memoria suficiente para el modelo mas preciso a "
              "buena velocidad.",
    },
    "recommend.gpu_medium": {
        "en": "Your {gpu} can run the medium model comfortably, which is clearly "
              "more accurate than the basic one.",
        "es": "Tu {gpu} puede con el modelo medium sin problema, que es claramente "
              "mas preciso que el basico.",
    },
    "recommend.cpu_medium": {
        "en": "With {cores} processor cores and {ram} GB of memory this computer "
              "can run the medium model. It is more accurate with names and "
              "figures, but takes roughly two and a half times longer.",
        "es": "Con {cores} nucleos y {ram} GB de memoria esta computadora puede "
              "con el modelo medium. Es mas preciso con nombres y cifras, pero "
              "tarda unas dos veces y media mas.",
    },
    "recommend.cpu_small": {
        "en": "The basic model is the right fit for this computer.",
        "es": "El modelo basico es el adecuado para esta computadora.",
    },
    "recommend.cpu_base": {
        "en": "This computer has limited memory, so a lighter model is safer. "
              "Expect more mistakes in the transcript.",
        "es": "Esta computadora tiene poca memoria, asi que conviene un modelo "
              "mas ligero. Espera mas errores en la transcripcion.",
    },

    # --- Environment check ------------------------------------------------
    "check.programs_header": {
        "en": "REQUIRED PROGRAMS",
        "es": "PROGRAMAS NECESARIOS",
    },
    "check.vision_header": {
        "en": "IMAGE MODELS (only needed to describe the video)",
        "es": "MODELOS DE IMAGEN (solo para describir el video)",
    },
    "check.no_vision": {
        "en": "None configured. Transcription still works; only the written "
              "account of the video is unavailable.",
        "es": "Ninguno configurado. La transcripcion funciona igual; solo el "
              "relato escrito del video no estara disponible.",
    },
    "check.settings_header": {"en": "CURRENT SETTINGS", "es": "AJUSTES ACTUALES"},
    "check.change_settings": {
        "en": "Change these in config.json, or override them in .env",
        "es": "Cambialos en config.json, o sobrescribelos en .env",
    },
    "check.missing_tool": {
        "en": "Something required is missing:",
        "es": "Falta algo necesario:",
    },
    "check.run_installer": {
        "en": "Run the installer first:  init.cmd  (Windows)  or  ./init.sh  (Mac/Linux)",
        "es": "Corre primero el instalador:  init.cmd  (Windows)  o  ./init.sh  (Mac/Linux)",
    },

    # --- Model chooser ----------------------------------------------------
    "model.header": {
        "en": "CHOOSE HOW ACCURATE THE TRANSCRIPT SHOULD BE",
        "es": "ELIGE QUE TAN PRECISA QUIERES LA TRANSCRIPCION",
    },
    "model.explain": {
        "en": "A bigger model makes fewer mistakes but takes longer.",
        "es": "Un modelo mas grande se equivoca menos pero tarda mas.",
    },
    "model.col_model": {"en": "model", "es": "modelo"},
    "model.col_time": {"en": "time for this video", "es": "tiempo para este video"},
    "model.col_download": {"en": "download", "es": "descarga"},
    "model.col_status": {"en": "status", "es": "estado"},
    "model.too_big": {
        "en": "too big for this computer",
        "es": "muy grande para esta computadora",
    },
    "model.recommended": {"en": "recommended", "es": "recomendado"},
    "model.current": {"en": "current setting", "es": "ajuste actual"},
    "model.downloaded": {"en": "already downloaded", "es": "ya descargado"},
    "model.not_here_yet": {
        "en": "'{model}' is not on this computer yet ({size} MB).",
        "es": "'{model}' todavia no esta en esta computadora ({size} MB).",
    },
    "model.downloads_once": {
        "en": "It downloads once, automatically, the first time it runs.",
        "es": "Se descarga una sola vez, automaticamente, la primera vez que corre.",
    },
    "model.download_confirm": {
        "en": "Download it when the run starts?",
        "es": "Descargarlo cuando empiece el proceso?",
    },

    # --- Run summary ------------------------------------------------------
    "run.about_to": {
        "en": "About to process {count} video(s) with model '{model}'.",
        "es": "Se procesaran {count} video(s) con el modelo '{model}'.",
    },
    "run.rough_time": {
        "en": "Rough total time: {time}",
        "es": "Tiempo total aproximado: {time}",
    },
    "run.plus_description": {
        "en": " plus the video description.",
        "es": " mas la descripcion del video.",
    },
    "run.leave_running": {
        "en": "You can leave this running; progress is shown for every step.",
        "es": "Puedes dejarlo corriendo; se muestra el avance de cada paso.",
    },
    "run.vision_will_use": {
        "en": "Video description will use: {backend}",
        "es": "La descripcion del video usara: {backend}",
    },
    "run.no_vision_options": {
        "en": "The video description needs an image-capable model, and none is "
              "configured on this computer. Your options:",
        "es": "La descripcion del video necesita un modelo que vea imagenes, y no "
              "hay ninguno configurado. Tus opciones:",
    },
    "run.no_vision_claude": {
        "en": "- install the 'claude' command from https://claude.com/claude-code",
        "es": "- instala el comando 'claude' desde https://claude.com/claude-code",
    },
    "run.no_vision_key": {
        "en": "- or put an API key in .env (Anthropic, OpenAI or Google Gemini)",
        "es": "- o pon una clave de API en .env (Anthropic, OpenAI o Google Gemini)",
    },
    "run.continue_transcript_only": {
        "en": "Continue with the transcript only?",
        "es": "Continuar solo con la transcripcion?",
    },

    # --- Pipeline steps ---------------------------------------------------
    "step.reading": {
        "en": "Reading the video file",
        "es": "Leyendo el archivo de video",
    },
    "step.extracting_audio": {
        "en": "Extracting the audio",
        "es": "Extrayendo el audio",
    },
    "step.transcribing": {
        "en": "Converting speech to text",
        "es": "Convirtiendo voz en texto",
    },
    "step.speakers": {
        "en": "Telling the speakers apart",
        "es": "Separando a las personas que hablan",
    },
    "step.writing_transcript": {
        "en": "Writing the transcript files",
        "es": "Escribiendo los archivos de transcripcion",
    },
    "step.extracting_frames": {
        "en": "Extracting video frames",
        "es": "Extrayendo fotogramas del video",
    },
    "step.describing": {
        "en": "Describing the video with '{backend}'",
        "es": "Describiendo el video con '{backend}'",
    },
    "step.writing_account": {
        "en": "Writing the final account",
        "es": "Redactando el relato final",
    },

    # --- Pipeline details -------------------------------------------------
    "detail.length": {"en": "Length {duration}", "es": "Duracion {duration}"},
    "detail.picture": {"en": ", picture {width}x{height}", "es": ", imagen {width}x{height}"},
    "detail.estimate": {
        "en": "Transcription with '{model}' should take {time}",
        "es": "La transcripcion con '{model}' deberia tardar {time}",
    },
    "detail.already_extracted": {
        "en": "Already extracted, reusing it",
        "es": "Ya estaba extraido, se reutiliza",
    },
    "detail.model_threads": {
        "en": "Model '{model}', language '{language}', {threads} threads",
        "es": "Modelo '{model}', idioma '{language}', {threads} hilos",
    },
    "detail.first_download": {
        "en": "The first run of a model downloads it; later runs start immediately.",
        "es": "La primera vez que se usa un modelo se descarga; despues arranca al instante.",
    },
    "detail.reusing_transcript": {
        "en": "Reusing the existing transcript ({count} segments)",
        "es": "Se reutiliza la transcripcion existente ({count} segmentos)",
    },
    "detail.speakers_found": {
        "en": "{count} speaker(s) identified",
        "es": "{count} persona(s) identificada(s)",
    },
    "detail.speech_time": {
        "en": "{speaker}: {duration} of speech",
        "es": "{speaker}: {duration} hablando",
    },
    "detail.frames_every": {
        "en": "{count} frames, one every {interval} seconds",
        "es": "{count} fotogramas, uno cada {interval} segundos",
    },
    "detail.reusing_frames": {
        "en": "Reusing {count} frames already extracted",
        "es": "Se reutilizan {count} fotogramas ya extraidos",
    },
    "detail.sections_failed": {
        "en": "{count} section(s) failed. Re-run with --resume to retry only those.",
        "es": "{count} seccion(es) fallaron. Vuelve a correr con --resume para reintentar solo esas.",
    },
    "detail.sections_described": {
        "en": "{done} of {total} sections described",
        "es": "{done} de {total} secciones descritas",
    },
    "detail.invented_removed": {
        "en": "({count} invented timecode(s) removed)",
        "es": "({count} marca(s) de tiempo inventada(s) eliminada(s))",
    },

    # --- Progress bar words ----------------------------------------------
    "bar.extracted": {"en": "extracted", "es": "extraido"},
    "bar.transcribed": {"en": "transcribed", "es": "transcrito"},
    "bar.grouped": {"en": "grouped", "es": "agrupado"},
    "bar.written": {"en": "written", "es": "escrito"},
    "bar.reused": {"en": "reused", "es": "reutilizado"},
    "bar.done_in": {"en": "done in {time}", "es": "listo en {time}"},

    # --- Warnings and errors ---------------------------------------------
    "warn.speakers_unclear": {
        "en": "The voices did not separate cleanly (best score {score}, where "
              "1.00 means no structure at all). Treat the speaker labels as a "
              "rough guide, and consider re-running with an explicit speaker count.",
        "es": "Las voces no se separaron con claridad (mejor indice {score}, donde "
              "1.00 significa que no hay estructura). Toma las etiquetas de "
              "persona como una guia aproximada, y considera volver a correr "
              "indicando cuantas personas hablan.",
    },
    "warn.vision_skipped": {
        "en": "Visual description skipped: no image model configured.",
        "es": "Se omitio la descripcion visual: no hay modelo de imagen configurado.",
    },
    "error.no_audio": {
        "en": "{name} has no audio track, so there is nothing to transcribe.",
        "es": "{name} no tiene pista de audio, asi que no hay nada que transcribir.",
    },
    "error.no_speech": {
        "en": "No speech was detected in this recording.",
        "es": "No se detecto voz en esta grabacion.",
    },
    "error.span_outside": {
        "en": "The requested stretch falls outside the video.",
        "es": "El tramo solicitado queda fuera del video.",
    },
    "error.no_sections": {
        "en": "No section could be described; the visual account cannot be written.",
        "es": "No se pudo describir ninguna seccion; no se puede redactar el relato visual.",
    },
    "error.stopped": {
        "en": "Stopped. Re-run with --resume to carry on where this left off.",
        "es": "Detenido. Vuelve a correr con --resume para continuar donde se quedo.",
    },
    # --- doctor and models screens ---------------------------------------
    "doctor.computer": {"en": "THIS COMPUTER", "es": "ESTA COMPUTADORA"},
    "doctor.vision_header": {
        "en": "IMAGE MODELS (optional, for describing the picture)",
        "es": "MODELOS DE IMAGEN (opcional, para describir la imagen)",
    },
    "doctor.recommendation": {"en": "RECOMMENDATION", "es": "RECOMENDACION"},
    "doctor.model_line": {
        "en": "Transcription model: {model}",
        "es": "Modelo de transcripcion: {model}",
    },
    "doctor.folders": {"en": "FOLDERS", "es": "CARPETAS"},
    "doctor.videos_in": {"en": "Videos in : {path}", "es": "Videos en     : {path}"},
    "doctor.results_in": {"en": "Results in: {path}", "es": "Resultados en : {path}"},
    "doctor.settings": {"en": "SETTINGS IN USE", "es": "AJUSTES EN USO"},
    "doctor.missing_count": {
        "en": "{count} required item(s) missing. Run init.cmd or ./init.sh",
        "es": "Faltan {count} elemento(s) necesario(s). Corre init.cmd o ./init.sh",
    },
    "models.header": {
        "en": "TRANSCRIPTION MODELS, TIMED FOR THIS COMPUTER",
        "es": "MODELOS DE TRANSCRIPCION, MEDIDOS PARA ESTA COMPUTADORA",
    },
    "models.for_one_hour": {
        "en": "Estimates are for one hour of video.",
        "es": "Los tiempos son para una hora de video.",
    },
    "models.needs_memory": {
        "en": "needs more memory than this computer has",
        "es": "necesita mas memoria de la que tiene esta computadora",
    },
    "models.recommended_here": {"en": "recommended here", "es": "recomendado aqui"},
    "models.change_with": {
        "en": "Change the model with:  --model medium",
        "es": "Cambia el modelo con:  --model medium",
    },
    "models.or_permanently": {
        "en": "Or permanently in config.json under transcription.model",
        "es": "O de forma permanente en config.json, en transcription.model",
    },

    # --- spoken durations -------------------------------------------------
    "duration.under_two_minutes": {
        "en": "less than 2 minutes", "es": "menos de 2 minutos",
    },
    "duration.minutes": {"en": "about {value} minutes", "es": "unos {value} minutos"},
    "duration.hours": {"en": "about {value} hours", "es": "unas {value} horas"},

    "detail.transcript_summary": {
        "en": "{count} segments, language {language} "
              "(confidence {confidence}), duration {duration}",
        "es": "{count} segmentos, idioma {language} "
              "(confianza {confidence}), duracion {duration}",
    },

    # --- Output files -----------------------------------------------------
    # These appear inside the documents the user hands to someone else, so
    # they must follow the chosen language just as the menus do.
    "file.transcript_title": {
        "en": "TRANSCRIPT WITH SPEAKER IDENTIFICATION",
        "es": "TRANSCRIPCION CON IDENTIFICACION DE PERSONAS",
    },
    "file.narrative_title": {
        "en": "WRITTEN ACCOUNT OF THE VIDEO (sound and image)",
        "es": "RELATO ESCRITO DEL VIDEO (audio e imagen)",
    },
    "file.source": {"en": "Source file", "es": "Archivo de origen"},
    "file.covers": {"en": "Covers", "es": "Abarca"},
    "file.covers_value": {
        "en": "{start} to {end} of the source video",
        "es": "de {start} a {end} del video original",
    },
    "file.duration": {"en": "Duration", "es": "Duracion"},
    "file.language": {"en": "Language", "es": "Idioma"},
    "file.language_value": {
        "en": "{code} (confidence {confidence})",
        "es": "{code} (confianza {confidence})",
    },
    "file.model": {"en": "Model", "es": "Modelo"},
    "file.speakers_found": {"en": "Speakers found", "es": "Personas detectadas"},
    "file.generated": {"en": "Generated", "es": "Generado"},
    "file.please_note": {"en": "Please note", "es": "Aviso"},
    "file.based_on": {"en": "Based on", "es": "Se basa en"},
    "file.based_on_value": {
        "en": "{frames} frames (one every {interval}s) and {segments} speech segments",
        "es": "{frames} fotogramas (uno cada {interval}s) y {segments} segmentos de voz",
    },
    "file.described_by": {"en": "Described by", "es": "Descrito por"},
    "file.disclaimer": {
        "en": "This file was produced automatically by speech recognition and, "
              "where a visual description is included, by an image model. Both "
              "make mistakes. Check every figure, name and job title against "
              "the recording before relying on it. Each timecode points at the "
              "moment in the video where the statement can be verified.",
        "es": "Este archivo se genero automaticamente con reconocimiento de voz "
              "y, cuando incluye descripcion visual, con un modelo de imagen. "
              "Ambos se equivocan. Verifica cada cifra, nombre y cargo contra la "
              "grabacion antes de darle uso. Cada marca de tiempo apunta al "
              "momento del video donde se puede comprobar lo afirmado.",
    },
    "file.sections_title": {
        "en": "Written account by section - {name}",
        "es": "Relato por tramos - {name}",
    },
    "file.sections_intro": {
        "en": "Each section covers one stretch of the recording. The heading is "
              "the time at which the stretch begins.",
        "es": "Cada tramo cubre un fragmento de la grabacion. El encabezado es "
              "el momento en que empieza ese fragmento.",
    },

    # --- Folder guide (00_READ_ME_FIRST.txt) ------------------------------
    "readme.title": {
        "en": "WHAT IS IN THIS FOLDER", "es": "QUE HAY EN ESTA CARPETA",
    },
    "readme.important": {"en": "IMPORTANT", "es": "IMPORTANTE"},
    "readme.warning": {
        "en": "These files were produced automatically. Speech recognition "
              "mishears words, especially names and numbers, and the visual "
              "description can misread small print. Before relying on any "
              "statement, open the video at the timecode shown in square "
              "brackets and confirm it yourself.",
        "es": "Estos archivos se generaron automaticamente. El reconocimiento "
              "de voz confunde palabras, sobre todo nombres y cifras, y la "
              "descripcion visual puede leer mal la letra chica. Antes de "
              "apoyarte en cualquier afirmacion, abre el video en la marca de "
              "tiempo entre corchetes y compruebalo tu mismo.",
    },
    "readme.work_folder": {
        "en": "The 'work' folder holds temporary files and can be deleted.",
        "es": "La carpeta 'work' tiene archivos temporales y se puede borrar.",
    },
    "readme.data_folder": {
        "en": "The 'data' folder is needed if you want to re-run a step later.",
        "es": "La carpeta 'data' hace falta si quieres rehacer un paso despues.",
    },
    "readme.file_audio": {
        "en": "The sound of the video on its own.",
        "es": "El sonido del video, por separado.",
    },
    "readme.file_transcript": {
        "en": "Who said what, with the time of each turn.",
        "es": "Quien dijo que, con el minuto de cada intervencion.",
    },
    "readme.file_subtitles": {
        "en": "The same text as subtitles; open it with the video.",
        "es": "El mismo texto como subtitulos; abrelo junto con el video.",
    },
    "readme.file_narrative": {
        "en": "A written account of what happens in the video.",
        "es": "Un relato escrito de lo que ocurre en el video.",
    },
    "readme.file_sections": {
        "en": "The same account, split into short sections.",
        "es": "El mismo relato, dividido en tramos cortos.",
    },
    "readme.file_data": {
        "en": "Machine-readable files. Keep these to re-run a step later.",
        "es": "Archivos para la maquina. Conservalos para rehacer un paso.",
    },
    "readme.file_work": {
        "en": "Temporary files. Safe to delete.",
        "es": "Archivos temporales. Se pueden borrar.",
    },

    # --- Offering to install a missing program ----------------------------
    "install.offer_header": {
        "en": "SHALL I INSTALL IT FOR YOU?",
        "es": "QUIERES QUE LO INSTALE?",
    },
    "install.explain": {
        "en": "ffmpeg is the program that reads video files. VideoScribe cannot "
              "do anything without it. It is free and open source.",
        "es": "ffmpeg es el programa que lee los archivos de video. VideoScribe "
              "no puede hacer nada sin el. Es gratuito y de codigo abierto.",
    },
    "install.option_none": {
        "en": "Not now, I will install it myself",
        "es": "Ahora no, lo instalo yo mismo",
    },
    "install.needs_admin": {
        "en": "(needs administrator permission)",
        "es": "(necesita permiso de administrador)",
    },
    "install.working": {"en": "Installing...", "es": "Instalando..."},
    "install.success": {
        "en": "ffmpeg is ready. Carrying on.",
        "es": "ffmpeg esta listo. Continuamos.",
    },
    "install.failed": {
        "en": "That did not work. Try the other option, or install ffmpeg by hand.",
        "es": "No funciono. Prueba la otra opcion, o instala ffmpeg a mano.",
    },
    "install.downloading": {
        "en": "Downloading  {done} MB of {total} MB",
        "es": "Descargando  {done} MB de {total} MB",
    },
    "install.no_options": {
        "en": "This computer has no package manager and no portable build is "
              "available for it, so ffmpeg has to be installed by hand.",
        "es": "Esta computadora no tiene gestor de paquetes y no hay una version "
              "portable para ella, asi que ffmpeg se tiene que instalar a mano.",
    },

    # --- "when to use it" column in the model chooser ---------------------
    "prompt.yes_letter": {"en": "y", "es": "s"},
    "prompt.no_letter": {"en": "n", "es": "n"},
    "model.col_when": {"en": "when to use it", "es": "cuando usarlo"},
    "model.when_tiny": {
        "en": "a quick look, to check the sound is usable",
        "es": "un vistazo rapido, para ver si el audio sirve",
    },
    "model.when_base": {"en": "still rough", "es": "todavia tosco"},
    "model.when_small": {"en": "good balance", "es": "buen equilibrio"},
    "model.when_medium": {
        "en": "clearly better with names and figures",
        "es": "claramente mejor con nombres y cifras",
    },
    "model.when_large": {
        "en": "the best there is; heavy without a graphics card",
        "es": "lo mejor que hay; pesado sin tarjeta grafica",
    },
    "model.measured_for": {
        "en": "Times are measured for your video ({duration}) on this computer.",
        "es": "Los tiempos estan medidos para tu video ({duration}) en esta computadora.",
    },

    # --- Setting up an image model ----------------------------------------
    "vision.header": {
        "en": "HOW SHOULD THE VIDEO BE DESCRIBED?",
        "es": "COMO SE DEBE DESCRIBIR EL VIDEO?",
    },
    "vision.explain": {
        "en": "Reading the picture needs a model that can see images. The "
              "transcript never needs this; only the description does.",
        "es": "Leer la imagen necesita un modelo que vea fotos. La transcripcion "
              "nunca lo necesita; solo la descripcion.",
    },
    "vision.option_local": {
        "en": "On this computer, with Ollama",
        "es": "En esta computadora, con Ollama",
    },
    "vision.option_local_detail": {
        "en": "free, private, nothing leaves the machine; slower and worse at "
              "small print",
        "es": "gratis, privado, nada sale de la computadora; mas lento y peor "
              "con la letra chica",
    },
    "vision.option_key": {
        "en": "Paste an API key",
        "es": "Pegar una clave de API",
    },
    "vision.option_key_detail": {
        "en": "best quality and much faster; the provider charges per use and "
              "the frames are sent to them",
        "es": "mejor calidad y mucho mas rapido; el proveedor cobra por uso y "
              "los fotogramas se le envian",
    },
    "vision.option_claude": {
        "en": "Install the Claude Code command",
        "es": "Instalar el comando de Claude Code",
    },
    "vision.option_claude_detail": {
        "en": "included in a Claude subscription, no API key needed",
        "es": "incluido en una suscripcion de Claude, sin clave de API",
    },
    "vision.option_skip": {
        "en": "Skip it, transcript only",
        "es": "Omitirlo, solo transcripcion",
    },
    "vision.choose_provider": {
        "en": "Which provider is the key from?",
        "es": "De que proveedor es la clave?",
    },
    "vision.paste_key": {
        "en": "Paste the key and press Enter (it will not be shown)",
        "es": "Pega la clave y presiona Enter (no se mostrara)",
    },
    "vision.key_saved": {
        "en": "Saved in .env. It stays on this computer and is never committed.",
        "es": "Guardada en .env. Se queda en esta computadora y nunca se sube.",
    },
    "vision.key_empty": {"en": "Nothing was pasted.", "es": "No se pego nada."},
    "vision.key_where": {
        "en": "Get one at: {url}",
        "es": "Consiguela en: {url}",
    },
    "vision.ollama_missing": {
        "en": "Ollama is not installed. It is a free program that runs the model "
              "on this computer. Install it from https://ollama.com and come back.",
        "es": "Ollama no esta instalado. Es un programa gratuito que corre el "
              "modelo en esta computadora. Instalalo desde https://ollama.com "
              "y vuelve.",
    },
    "vision.ollama_model": {
        "en": "Model for this computer: {model} (about {size} GB to download)",
        "es": "Modelo para esta computadora: {model} (unos {size} GB de descarga)",
    },
    "vision.ollama_slow": {
        "en": "Roughly {minutes} minutes to describe this video on a CPU, against "
              "a few minutes with a cloud model. It reads large signs well and "
              "small embroidered text poorly.",
        "es": "Unos {minutes} minutos para describir este video en CPU, contra "
              "unos pocos con un modelo en la nube. Lee bien los letreros "
              "grandes y mal el texto bordado pequeno.",
    },
    "vision.ollama_pull": {
        "en": "Download the model now? Ollama does it once.",
        "es": "Descargar el modelo ahora? Ollama lo hace una sola vez.",
    },
    "vision.ollama_ready": {
        "en": "Ready. The video will be described on this computer.",
        "es": "Listo. El video se describira en esta computadora.",
    },
    "vision.found": {
        "en": "Found and ready: {backend}",
        "es": "Encontrado y listo: {backend}",
    },

    "detail.parallel_parts": {
        "en": "Splitting into {parts} parts transcribed at the same time, "
              "{threads} threads each",
        "es": "Se divide en {parts} partes transcritas al mismo tiempo, "
              "{threads} hilos cada una",
    },

}


def detect_system_language() -> str:
    """Guess the language from the operating system, defaulting to English.

    The environment variables are consulted first because they are what a user
    actually controls. ``locale.getlocale`` is the fallback; the older
    ``getdefaultlocale`` is avoided because it is deprecated for removal.
    """
    code = (
        os.environ.get("LANGUAGE")
        or os.environ.get("LC_ALL")
        or os.environ.get("LANG")
        or ""
    ).split(":")[0]

    if not code:
        try:
            code = locale.getlocale()[0] or ""
        except (ValueError, TypeError):
            code = ""

    prefix = str(code).split("_")[0].split("-")[0].split(".")[0].lower()
    return prefix if prefix in LANGUAGE_NAMES else DEFAULT_LANGUAGE


def set_language(code: str) -> str:
    """Set the language for every later :func:`t` call. Returns what was set."""
    global _current
    normalised = (code or "").strip().lower()[:2]
    _current = normalised if normalised in LANGUAGE_NAMES else DEFAULT_LANGUAGE
    return _current


def get_language() -> str:
    return _current


def language_name(code: str | None = None) -> str:
    return LANGUAGE_NAMES.get(code or _current, LANGUAGE_NAMES[DEFAULT_LANGUAGE])


def t(key: str, **values) -> str:
    """Look up a message in the current language and fill in its placeholders.

    An unknown key returns the key itself rather than raising. A missing
    translation falls back to English. Both make a gap in the catalogue
    visible on screen without stopping a long run that was otherwise working.
    """
    entry = MESSAGES.get(key)
    if entry is None:
        return key
    text = entry.get(_current) or entry.get(DEFAULT_LANGUAGE, key)
    if not values:
        return text
    try:
        return text.format(**values)
    except (KeyError, IndexError):
        return text
