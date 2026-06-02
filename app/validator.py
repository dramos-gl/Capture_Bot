import re
import logging

logger = logging.getLogger("OptimaCaptureBot.Validator")

# Expresión regular oficial del SAT para validar RFC (Persona Física o Moral)
# 3 o 4 letras iniciales, 6 dígitos de fecha, y 3 caracteres de homoclave.
RFC_REGEX = re.compile(r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$", re.IGNORECASE)

def validar_rfc(rfc):
    """
    Valida si un RFC cumple con la estructura sintáctica oficial del SAT.
    """
    if not rfc:
        return False, "El RFC está vacío o es nulo."
    
    rfc_clean = str(rfc).strip().upper()
    if RFC_REGEX.match(rfc_clean):
        return True, ""
    return False, f"El formato del RFC '{rfc}' no es válido según el estándar oficial del SAT."

def validar_referencia(referencia):
    """
    Valida sintácticamente la referencia: no vacía, sin caracteres extraños de control,
    y con una longitud prudente para búsquedas en SATQ.
    """
    if not referencia:
        return False, "La referencia está vacía."
    
    ref_clean = str(referencia).strip()
    if len(ref_clean) < 6:
        return False, f"La referencia '{referencia}' es demasiado corta (mínimo 6 caracteres)."
        
    # Verificar caracteres prohibidos que puedan romper búsquedas
    if any(char in ref_clean for char in ["'", '"', "\\", "*", "?", "<", ">", "|"]):
        return False, f"La referencia '{referencia}' contiene caracteres especiales no válidos."
        
    return True, ""

def validar_duplicados_locales(registros):
    """
    Barre los registros cargados de Excel e identifica duplicados internos de la sesión activa
    (misma referencia en el mismo lote).
    Retorna un conjunto con los índices de filas duplicadas para marcarlos preventivamente.
    """
    duplicados = set()
    vistos = {} # llave: referencia, valor: indice de fila
    
    for reg in registros:
        ref = reg["referencia"]
        fila = reg["fila_excel"]
        
        # Solo comparamos registros que están pendientes de procesar
        if reg["estado"] in ["PENDIENTE", "VALIDADO"]:
            if ref in vistos:
                duplicados.add(fila)
                # También añadimos el primero visto para marcar ambos como duplicados
                duplicados.add(vistos[ref])
            else:
                vistos[ref] = fila
                
    if duplicados:
        logger.warning(f"Se detectaron {len(duplicados)} registros con referencias duplicadas en este lote.")
        
    return duplicados
