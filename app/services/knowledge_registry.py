from importlib import import_module

def get_dimension_knowledge(slug: str):
    try:
        module = import_module(f"app.knowledge.{slug}")
        if hasattr(module, "knowledge"):
            return module.knowledge

        for attr in dir(module):
            if attr.endswith("_knowledge"):
                return getattr(module, attr)

        return None
    except Exception:
        return None
