# Qué creer, y qué verificar

[English](ACCURACY.md) · **Español**

Esta página existe porque la respuesta honesta a "¿qué tan preciso es?" es "depende,
y aquí está exactamente dónde falla". Si vas a citar este resultado frente a un juez,
un cliente o un editor, lee esto primero.

## En resumen

| Parte del resultado | ¿Le crees? | Qué hacer |
|---|---|---|
| **Las marcas de tiempo** | Sí | Se calculan con aritmética, no se adivinan |
| **Las palabras dichas** | Casi siempre | Revisa nombres, cifras y términos técnicos |
| **Quién lo dijo** | **La parte menos confiable** | Verifícalo de oído antes de citarlo |
| **Lo que se ve** | Casi siempre | Revisa todo lo pequeño: gafetes, letra chica, cifras |
| **La interpretación** | Viene marcada como tal | Lee "aparentemente" como "el programa está adivinando" |

---

## Las marcas de tiempo

Es lo único en lo que puedes confiar de verdad, y todo el diseño está armado para
que siga siendo así.

- **Se truncan, nunca se redondean.** En el segundo 40.7 la etiqueta es `00:00:40`,
  porque `00:00:41` podría ser ya la siguiente frase.
- Siempre se refieren al **video original**, aunque solo hayas procesado un tramo
  con `--start`. Escribe una en el reproductor y caes en el momento correcto.
- Las marcas de tiempo del relato visual **se comparan contra los tiempos reales de
  fotogramas y transcripción** de ese tramo. Las que el modelo se inventó se borran
  antes de que las veas.

Ese último punto importa. Los modelos de lenguaje estiman los tiempos cuando se les
pide citarlos. En pruebas, una corrida citó `[00:02:33]` para una línea que en
realidad estaba en `[00:01:38]`. La validación ahora lo detecta; cuando se activa,
ves una nota que dice cuántas se eliminaron.

---

## Las palabras

La calidad del reconocimiento de voz depende del modelo que elegiste, del audio y
del idioma configurado.

**En qué se equivoca, sin falta:**

- **Nombres propios.** Casi siempre. Un nombre que se oye una sola vez casi siempre
  sale mal.
- **Cifras.** "1780" y "17" se confunden fácil; "el 12" y "el 13" también.
- **Voces encimadas.** Cuando dos personas hablan al mismo tiempo, normalmente se
  pierde una.
- **Vocabulario jurídico y técnico** que no es común en el habla diaria.
- **Repeticiones falsas.** A veces el modelo escribe la misma frase dos veces donde
  hay un silencio. Si ves una línea duplicada, revisa el audio antes de suponer que
  la persona se repitió.

**Qué ayuda:**

- Fija el idioma en lugar de dejar `auto`. Es la causa más común, por mucho, de un
  mal resultado.
- Usa un modelo más grande. `medium` es claramente mejor que `small` con nombres y
  cifras, a cambio de unas 2.6 veces más tiempo.
- Saca primero una muestra de tres minutos (`--start` / `--duration`) para comprobar
  que el audio sirve antes de comprometerte a un proceso largo.

---

## Quién dijo qué

**Esta es la parte más débil de la herramienta. Toma las etiquetas de persona como
un primer borrador.**

### Cómo funciona

Cada fragmento de habla se describe con sus rasgos acústicos —el timbre de la voz
(MFCC) y su tono— y luego los fragmentos se agrupan por parecido. No hay un modelo
entrenado de cómo suena una persona; es un agrupamiento estadístico de sonidos.

### Por qué está hecho así

La alternativa, un modelo neuronal de voz como pyannote, es claramente mejor.
También exige descargar otro modelo, tener una cuenta de Hugging Face y aceptar una
licencia antes de que la herramienta siquiera arranque. Se decidió que dejar la
instalación en un solo `pip install`, sin cuenta en ningún lado, vale lo que cuesta
en precisión para este público.

Es una contrapartida asumida, no una afirmación de que el método actual sea bueno.

### Cuándo falla

Funciona cuando las voces son claramente distintas: un hombre y una mujer en un
cuarto callado. Falla cuando:

- Varias personas tienen voces parecidas
- La grabación tiene ruido, es al aire libre, o el cuarto hace eco
- Las personas están a distintas distancias del micrófono
- Alguien cambia el registro de su voz entre hablar tranquilo y alzar la voz

La falla más común es **partir a una persona en dos etiquetas**. En una grabación
real de 50 minutos probada durante el desarrollo, `Persona1` y `Persona3` resultaron
ser la misma persona durante tramos largos.

### Cómo te enteras

El programa te avisa:

```
! Las voces no se separaron con claridad (mejor índice 1.22, donde 1.00
  significa que no hay estructura). Toma las etiquetas de persona como una
  guía aproximada, y considera volver a correr indicando cuántas personas
  hablan.
```

El índice es la razón entre las distancias de unión del agrupamiento. Cerca de 1.00
quiere decir que los datos no tenían un corte natural, así que el número de personas
que se haya elegido es casi arbitrario. Arriba de 1.5, más o menos, la separación sí
significa algo.

### Cómo arreglarlo

Dile cuántas personas están hablando:

```bash
python videoscribe.py run --speakers 3 --resume
```

`--resume` reaprovecha la transcripción que ya existe, así que esto tarda segundos.
Prueba con el número que sepas que es el correcto; si no estás seguro, prueba dos o
tres valores y lee cuál reparte los turnos de forma que tenga sentido.

---

## El relato visual

### En qué es bueno

En pruebas, leyó correctamente (los ejemplos de aquí son inventados, no material de
un caso real):

- El rótulo `DIRECCIÓN DE PARQUES` en un vehículo
- Una placa de circulación
- Un letrero escrito a mano que decía `Renta De Cancha $40`
- El bordado de un uniforme, citado como parcialmente legible: `"...ano de Tal"`,
  `"...ección De Parques"`
- Una discrepancia que nadie le pidió buscar: el uniforme decía `2018-2021` mientras
  que un letrero en la pared decía `2022-2025`

### Qué revisar

- **La letra chica.** Nombres en gafetes, cifras en documentos, todo lo que esté al
  límite de lo legible. Cuando no está seguro, el modelo lo reporta como parcial
  (`"...ana de Tal"`), que es justo lo que quieres, pero el fragmento que sí reporta
  todavía puede estar mal.
- **Todo lo que le atribuya a una persona en concreto.** El modelo ve fotogramas, no
  un video continuo, y no siempre puede saber quién está hablando. Cuando en el audio
  hay una acusación, el relato debería decir que no puede ligar esas palabras con
  nadie que se vea en pantalla —y en las pruebas así lo hizo—, pero revísalo siempre.
- **Los huecos entre fotogramas.** Uno cada 10 segundos es lo predeterminado. Todo lo
  que pase entre dos fotogramas es invisible. Si un documento cambia de manos en tres
  segundos, puede que no aparezca en absoluto. Baja `--frame-interval` cuando importen
  las acciones breves.

### Qué significa "aparentemente"

Las instrucciones le exigen al modelo marcar con "aparentemente" o "parece" todo lo
que deduzca. Cuando veas esas palabras, léelas como: *el programa está adivinando,
verifica esto*.

---

## Lista práctica antes de confiar en esto

1. Abre `02_transcript.txt` y busca etiquetas de `Persona` que se alternen de forma
   inverosímil a media frase. Esa es la falla de la voz partida.
2. Busca en la transcripción cada cifra que importe y escucha esa marca de tiempo.
3. Busca cada nombre propio y escúchalo. Da por hecho que está mal hasta que lo hayas
   oído.
4. En `04_narrative.txt`, compara contra el video, en su marca de tiempo, cada texto
   legible que se cite.
5. Revisa todo lo que venga marcado con "aparentemente", "parece" o "parcialmente".
6. Si la corrida imprimió el aviso de que las voces no se separaron con claridad, no
   cites a quién se le atribuye algo sin antes escucharlo.

Nada de esto lleva mucho tiempo, porque cada línea trae su marca de tiempo. De eso se
trata.
