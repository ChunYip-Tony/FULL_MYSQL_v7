from __future__ import annotations

"""Refresh App Ready intelligence after authoritative True Stock mutations.

True Stock is an operator mutation and must be visible immediately.  The
canonical write functions remain unchanged; this wrapper only invalidates the
existing dependent caches and requests a replacement atomic snapshot after a
successful mutation. Readers continue seeing the previous complete generation
until the replacement promotes.
"""

from typing import Any, Callable


def _family_hint(args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> str | None:
    for source in (kwargs, result if isinstance(result, dict) else {}):
        for key in ("family_id", "family", "main_article_number", "article_number"):
            value = source.get(key) if isinstance(source, dict) else None
            if value not in (None, ""):
                return str(value)
    return None


def install_app_ready_true_stock_hook(app, api_module, request_rebuild: Callable[..., bool]) -> None:
    if getattr(app.state, "yipman_app_ready_true_stock_hook_installed", False):
        return

    names = (
        "submit_true_stock",
        "submit_negative_stock_true_stock",
        "cancel_true_stock",
        "v2_submit_family_true_stock",
    )
    installed: list[str] = []
    for name in names:
        base = getattr(api_module, name, None)
        if not callable(base) or getattr(base, "_yipman_app_ready_wrapped", False):
            continue

        def make_wrapper(fn, fn_name):
            def wrapped(*args, **kwargs):
                result = fn(*args, **kwargs)
                # Existing runtime cache invalidation is authoritative. It is
                # deliberately best-effort here because a successful physical
                # count must never be rolled back by cache-refresh plumbing.
                invalidate = getattr(api_module, "backoffice_invalidate_true_stock_dependent_caches", None)
                if callable(invalidate):
                    try:
                        invalidate()
                    except TypeError:
                        try:
                            invalidate(_family_hint(args, kwargs, result))
                        except Exception:
                            pass
                    except Exception:
                        pass
                request_rebuild(source_batch_id="TRUE_STOCK:" + fn_name + ":" + (_family_hint(args, kwargs, result) or "UNKNOWN"))
                return result
            wrapped._yipman_app_ready_wrapped = True
            wrapped._yipman_app_ready_base = fn
            return wrapped

        setattr(api_module, name, make_wrapper(base, name))
        installed.append(name)

    app.state.yipman_app_ready_true_stock_hook_installed = True
    app.state.yipman_app_ready_true_stock_mutations = tuple(installed)
