"""
CancunBot — Base Page
Clase base para todos los Page Objects.
Implementa el patrón anti-hardcodeo: resuelve localizadores desde BD.
"""
import logging
from playwright.sync_api import Page


class BasePage:
    """
    Clase base para todos los Page Objects de CancunBot.
    
    Los localizadores se cargan desde la tabla cancunbot_configuracion.localizador_portal
    y se resuelven en tiempo de ejecución, nunca están hardcodeados en el código.
    """

    def __init__(self, page: Page, localizadores: dict):
        """
        Args:
            page: Instancia de Page de Playwright
            localizadores: Dict cargado desde LocalizadorRepository.cargar_por_portal()
                          Formato: {nombre_clave: {estrategia_selector, valor_selector}}
        """
        self.page = page
        self.logger = logging.getLogger(self.__class__.__name__)
        self._locs = localizadores

    def _resolver(self, nombre_clave: str):
        """
        Resuelve un localizador desde el diccionario cargado de la BD.
        
        Args:
            nombre_clave: Identificador del localizador (ej: 'RECIBO_INPUT_FOLIO')
        
        Returns:
            Locator de Playwright listo para usar
        
        Raises:
            KeyError: Si el nombre_clave no existe en la BD
            ValueError: Si la estrategia de selector es desconocida
        """
        loc = self._locs.get(nombre_clave)
        if not loc:
            raise KeyError(
                f"Localizador '{nombre_clave}' no encontrado en la base de datos. "
                f"Verifica la tabla cancunbot_configuracion.localizador_portal."
            )

        estrategia = loc["estrategia_selector"]
        valor = loc["valor_selector"]

        self.logger.debug(f"Resolviendo localizador '{nombre_clave}': {estrategia}='{valor}'")

        match estrategia:
            case "CSS":
                return self.page.locator(valor)
            case "ID":
                return self.page.locator(f"#{valor}")
            case "TEXT":
                return self.page.get_by_text(valor)
            case "ROLE":
                # Formato esperado: "role|name" ej: "button|Consultar"
                partes = valor.split("|", 1)
                if len(partes) == 2:
                    return self.page.get_by_role(partes[0], name=partes[1])
                return self.page.get_by_role(partes[0])
            case "XPATH":
                return self.page.locator(f"xpath={valor}")
            case _:
                raise ValueError(
                    f"Estrategia de selector desconocida: '{estrategia}'. "
                    f"Valores válidos: CSS, ID, TEXT, ROLE, XPATH."
                )

    def esperar_carga(self, state: str = "networkidle") -> None:
        """Espera a que la página complete su carga."""
        self.page.wait_for_load_state(state)

    def esta_visible(self, nombre_clave: str) -> bool:
        """Verifica si un elemento es visible en la página actual."""
        try:
            return self._resolver(nombre_clave).is_visible()
        except Exception:
            return False
