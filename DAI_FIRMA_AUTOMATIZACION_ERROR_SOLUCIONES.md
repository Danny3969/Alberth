# PROBLEMA CON FIRMA DE ARCHIVOS DAI - ERROR DE AUTOMATIZACIÓN
**Elaborado por:** Alberth (Asistente técnico)
**Fecha:** 2026-07-17 11:35 GMT-5

---

## 📌 **CONTEXTO DESCRIPTO POR EL SEÑOR (DIRECTO)**
> "Yo no digo nada."  
> "Mira, ¿qué te pasa en esa foto?"
> "Tengo un problema para cuando estamos regularizando una DAI."
> "Me sale un error."
> "Pero es como cuando se genera el archivo y se lo descarga en la computadora."
> "Parece ser como que ese archivo está como de allá o no sé."
> "Aquí se le firma el código."
> "Sí, pero las demás sí se pueden firmar."
> "Pues se pueden que estén inspirando las cosas."
> "Ajá."
> "¿Y cuál es la firma?"
> "Es que dicen, las demás AUSOP las puedo firmar. Con la misma firma. Con la misma firma."

---

## 🔍 **INTERPRETACIÓN TÉCNICA (ALBERTH)**
El Señor menciona un **problema de firma digital/automatización para archivos DAI** (Documento Administrativo Interno).


### **Posibles causas identificadas:**



| **Síntoma**               | **Interpretación**                          | **Impacto**                                                    |
|----------------------------|--------------------------------------------|----------------------------------------------------------------|
| Error al generar archivo → descargar → firmar | **Interrupción en flujo automático**          | Incumplimiento en plazo de regularización DAI. No firma posible |
| "Ese archivo está como de allá"          | Posible problema de ruta de almacenamiento   | Archivo no encontrado por el sistema de firma automática.        |
| Firmas normales funcionan, pero DAI falla | **Configuración diferenciada o autoridad de firma** | Archivo DAI tiene restricción especial no aplicada a AUSOP.    |
| "Las demás AUSOP las puedo firmar con la misma firma" | Confusión de **permisos de firma digital** | Error en configuración de sellos/certificados específicos para tipos DAI. |

---

## 🚨 **RIESGOS SI NO SE RESUELVE**
- ❌ **Cumplimiento legal:** Plazos de regularización DAI incumplidos → multas o sanciones.
- ❌ **Pérdida de automatización:** El Señor menciona que el proceso **es automático**, pero falla en DAI → Retraso en todo el flujo.
- ❌ **Confianza en herramientas:** El Señor expresa frustración: "¿Qué te pasa en esa foto?" → Sistema fallando genera desconfianza.
- ❌ **Repetir trabajo:** "Inspirando las cosas" = ¿Problema de permisos o seguridad de archivo?


---

## ✅ **SOLUCIONES TÉCNICAS ACCIONABLES (HOY MISMO)**



### **1. DIAGNÓSTICO PRELIMINAR (5 minutos)**
**Paso 1:** Verificar ruta exacta del archivo generado:
```bash
echo "Ruta actual:"
pwd
ls -lh ~/Downloads/DAI_*
echo "Buscando archivos generados hoy:"
find ~/Downloads/ -name "*DAI*.pdf" -o -name "*DAI*.csv" -o -name "*DAI*.doc"
```
**Paso 2:** Revisar archivo generado → problema de:
- 🔹 Formato correcto (PDF/CSV).
- 🔹 Ruta del archivo en disco (¿Está en ~/Downloads/ o subcarpeta oculta?).
- 🔹 Permisos de escritura/lectura del archivo generado.

**Paso 3:** Revisar sistema de firma digital usado:
```bash
# En Mac terminal:
security find-certificate -a
security verify-cert -c "Certificado_Firma_DAI"
```
**Salida esperada:**
- Deberían listarse certificados instalados.
- Marcar si el certificado de firma específico para DAI está **caducado o no es confiable** (Trust Settings -> Always Trust).



### **2. CORRECCIÓN DE RUTA/ALMACENAMIENTO**
El Señor dijo: "Parece ser como que ese archivo está como de allá o no sé" → Posible archivo no está en ruta estándar de descarga.

**Solución inmediata:**
- 📍 **Revisar carpetas ocultas o estándar:**
  ```bash
  find ~ -name "*DAI*.pdf" -o -name "*DAI*.csv" 2>/dev/null | head -10
  ```
- 📍 **Verificar si archivo está en:**
  ```
  ~/.Trash/        → Papelera
  ~/Library/Containers/com.apple.mail/Data/Library/Mail Downloads/ → Descargas de Mail.app
  /private/tmp/    → Archivos temporales (requiere sudo para ver)
  ```
- 📍 **Mover archivo a carpeta de Descargas** si lo encuentra: `cp /ruta/oculta/DAI*.* ~/Downloads/`



### **3. CONFIGURACIÓN DE SELLO/CERTIFICADO AUTOMÁTICO**
**Problema identificado:** "Con la misma firma" para AUSOP vs DAI falla.

**Posibles causas:**
- ✅ **Certificado de firma por tipo de archivo** (DAI requiere certificado especial).
- ✅ **Permiso de firma en Keychain Access** → Configurar para confianza automática.
- ✅ **Ruta de script falla** → Script no usa la misma clave que el usuario principal.

**Solución:**


**A. Verificar Trust Settings para certificado de firma DAI:**
1. Abrir **Keychain Access** (🔍 → "Keychain Access").
2. Buscar certificado con nombre: **"Firma Digital DAI"**, **"Certificado Corporativo"**, o **"Razón Social"**. 
3. **Doble click en certificado** → Pestaña "Trust" → 
   - "When using this certificate:" → Seleccionar "Always Trust".
   - Cerrar ventana → Ingresar contraseña de Mac.

**B. Crear línea de comandos para fijar confianza automática (si usa terminal):**
```bash
# Buscar certificado que usa el flujo DAI:
security find-certificate -c "DAI"

# Corregir confianza (ejemplo con ID de certificado [ID_ejemplo])
sudo security set-trust-settings -c [ID_ejemplo] -p codeSign -t always
```
**Nota:** Reemplazar `[ID_ejemplo]` con ID real del certificado de DAI.

**C. Usar script de firma automática ajustado:**
**Ejemplo de ajuste para proceso DAI vs AUSOP:**
```python
import subprocess

def firmar_DAI_vs_AUSOP():    # Ruta de script que genera el archivo DAI
    ruta_archivo = "/Users/[USUARIO]/Downloads/DAI_Regularizacion_2026-07-17.pdf"
    
    if not os.path.exists(ruta_archivo):
        raise FileNotFoundError(f"Archivo DAI no encontrado en {ruta_archivo}")
    
    # Comando de firma usando certificado DAI
    comando_firma = [
        "/usr/bin/codesign", 
        "--sign", 
        "Certificado_DAI",  # Nombre del certificado en Keychain
        "--force",        
        "--verify",
        "-v",
        ruta_archivo
    ]
    
    resultado = subprocess.run(comando_firma, capture_output=True, text=True)
    if "successfully" in resultado.stdout.lower():
        print(f"✅ Archivo DAI firmado exitosamente: {ruta_archivo}")
    else:
        print(f"❌ Error en firma DAI: {resultado.stderr}")
        raise RuntimeError(resultado.stderr)
```
**Acción:** El script puede ajustarse para verificar que el certificado específico de DAI esté aplicado antes de firmar.



### **4. VALIDACIÓN AUTOMÁTICA POST-FIRMA (OPCIONAL)**
Si el flujo falla, agregar validación en Python:
```python
import os

def validar_firma_DAI(ruta_archivo):
    resultado = subprocess.run(
        ["/usr/bin/codesign", "-v", ruta_archivo],
        capture_output=True, text=True
    )
    return "succeeded" in resultado.stdout.lower()
```
**Nota:** Validar que clave de certificado específica esté en el archivo (trust chain).

---

## 📊 **MÉTRICAS DE ÉXITO (TIEMPO ESTIMADO)**

| **Acción**                             | **Tiempo**    | **Resultado esperado**                                  |
|-----------------------------------------|---------------|------------------------------------------------------|
| **Diagnóstico ruta archivo generado**      | 3 minutos     | Archivo DAI encontrado y movido a Descarga            |
| **Corregir Trust Settings certificado**   | 5 minutos     | Certificado de firma DAI configurado como "Always Trust" |
| **Probar firma automática post-cambio**    | 2 minutos     | Archivo DAI se firma con éxito → Uso correcto.       |
| **Validar script usa certificado correcto** | 5 minutos     | Script de firmas automatizadas en todos los casos.       |

---

## 📋 **CHECKLIST DE ACCIÓN INMEDIATA (TODAS OPERACIONES BLOQUEADAS POR SIGNATURE DAI)**

**Prioridad:** ERROR CRÍTICO (DAI no puede regularizarse).

- [ ] **Revisar ruta de archivo generado DAI:** `find ~ -name "*DAI*.pdf"`
- [ ] **Si existe archivo en ruta oculta:** Moverlo a ~/Downloads/
- [ ] **Abrir Keychain Access → validar certificado de firma."Firma Digital DAI"** → Trust Settings → Always Trust

- [ ] **Regenerar intentos de firma una vez hecha la corrección:**
  - Usar el código de firma concreto o GUI de su Mac (Automator/AppleScript si existe).
- [ ] **Si el error persiste:** Notificar a Soporte Técnico Infosec explicando el problema de ruta + certificado.
- [ ] **Validar solución:** Repetir proceso regulación DAI desde inicio.


---

## 🔄 **ESCALAMIENTO (SI FALLA CORRECCIÓN)**

| **Error encontrado**               | **Acción de escalamiento**                                                 |
|----------------------------------|---------------------------------------------------------------------------|
| Ruta de archivo es compartida      | Verificar permisos de escritura grupal (USERS/WORKGROUP)                     |
| Certificado caducado o inválido   | Llamar al proveedor de certificado (ej: SETEC) para renovación PROGRAMADA      |
| Error en script de firma           | Revisión de código + permisos de ejecución. Si no es interno → Contratar dev externo  |

---

## 📎 **DOCUMENTACIÓN PARA EL PROVEEDOR/DESARROLLADOR**
**Si requiere apoyo externo:**
- Derecho administrativo: DAI es trámite formal → Legal debe autorizar cambios.
- Soporte técnico: Nombre del certificado exacto usado para firma DAI.
- Error específico: Archivo generado vs archivo firmado = Error en ruta o permisos.

**Ejemplo de reporte:**
```
Hola Soporte,
Tengo un error en regularización automática DAI. El archivo generado en ~/Downloads/DAI_2026-07-17.pdf no puede firmarse.
La firma "Certificado_DAI" está configurada como AlwaysTrust en Keychain, pero el error persiste al intentar firmar:
CMD: /usr/bin/codesign --sign "Certificado_DAI" --force archivo.pdf → "Failed to code sign" 
¿Dónde puede estar el error? Ruta y permisos chequeados. 
Gracias,
[Señor Danny] (escalado por Alberth)
```

---

## 💡 **RECOMENDACIÓN FINAL (ALBERTH)**
1. **La causa más probable es el certificado DAI** → Revisar Trust Settings en Keychain Access.
2. **Verifique primero ruta del archivo generado** (si no está en ~/Downloads/, es la falla).
3. **Si error persiste después de solucionar certificado:** Notificar a soporte externo explicando ruta + certificado fallido.

---

## 📚 **NOTA INTERNA PARA ALBERTH**
**Si no hay éxito en 2 horas:**
- Preguntar al Señor Danny si acepta que Alberth **escriba un script de validación-checksum** para evitar que se genere el archivo corrupto. 
- Solución Bonus: Crear `validar_DAI.sh` que:
  - Verifique checkbox de archivo generado.
  - Verifique certificado trust settings.
  - Ejecute firma con script de Python como respaldo.

---
**Generado por Alberth - Última actualización:** 2026-07-17 11:35 GMT-5
**Impacto:** Si esto no se soluciona, **no hay procesos automáticos que funcionen para DAI**. Prioridad crítica en legal y compliance.