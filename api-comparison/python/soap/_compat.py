"""Shim de compatibilidade Spyne 2.14 + Python 3.12.

Sob Python 3.12 o importer do `six` vendorizado pelo Spyne usa a API antiga
`find_module` (removida), então `spyne.util.six.moves` deixa de resolver.
Os demais utilitários do six vendorizado (ex: get_function_name) continuam
necessários, portanto NÃO redirecionamos o módulo inteiro — apenas a subárvore
`.moves` é mapeada para o pacote `six` real (que possui `find_spec`).
Importar este módulo ANTES de qualquer import de spyne.
"""
import sys
import importlib
import importlib.abc
import importlib.util
import six          # noqa: F401
import six.moves    # noqa: F401

_SRC = "spyne.util.six.moves"
_DST = "six.moves"


class _MovesRedirect(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, fullname, path, target=None):
        if fullname == _SRC or fullname.startswith(_SRC + "."):
            return importlib.util.spec_from_loader(fullname, self)
        return None

    def create_module(self, spec):
        target = _DST + spec.name[len(_SRC):]
        return importlib.import_module(target)

    def exec_module(self, module):
        pass


if not any(isinstance(f, _MovesRedirect) for f in sys.meta_path):
    sys.meta_path.insert(0, _MovesRedirect())
