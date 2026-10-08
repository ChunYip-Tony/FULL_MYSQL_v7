from __future__ import annotations
"""Refresh App Ready intelligence after authoritative True Stock mutations.

The physical-count mutation is authoritative. Refresh plumbing is strictly
post-commit/best-effort: a cache or rebuild failure must never turn a committed
True Stock write into an HTTP failure that invites the operator to submit it
again.
"""
from typing import Any,Callable

def _family_hint(args:tuple[Any,...],kwargs:dict[str,Any],result:Any)->str|None:
    for source in (kwargs,result if isinstance(result,dict) else {}):
        for key in ('family_id','family','main_article_number','article_number'):
            value=source.get(key) if isinstance(source,dict) else None
            if value not in (None,''):return str(value)
    return None

def install_app_ready_true_stock_hook(app,api_module,request_rebuild:Callable[...,bool])->None:
    if getattr(app.state,'yipman_app_ready_true_stock_hook_installed',False):return
    names=('submit_true_stock','submit_negative_stock_true_stock','cancel_true_stock','v2_submit_family_true_stock');installed=[]
    for name in names:
        base=getattr(api_module,name,None)
        if not callable(base) or getattr(base,'_yipman_app_ready_wrapped',False):continue
        def make_wrapper(fn,fn_name):
            def wrapped(*args,**kwargs):
                # Exceptions from the authoritative mutation propagate normally;
                # therefore no refresh is requested for a failed write.
                result=fn(*args,**kwargs)
                family=_family_hint(args,kwargs,result)
                invalidate=getattr(api_module,'backoffice_invalidate_true_stock_dependent_caches',None)
                if callable(invalidate):
                    try:invalidate()
                    except TypeError:
                        try:invalidate(family)
                        except Exception:pass
                    except Exception:pass
                try:
                    request_rebuild(source_batch_id='TRUE_STOCK:'+fn_name+':'+(family or 'UNKNOWN'))
                except Exception:
                    # The DB mutation is already committed. Never report it as
                    # failed merely because asynchronous read-model refresh had
                    # a transient problem. A later publish/startup rebuild heals it.
                    pass
                return result
            wrapped._yipman_app_ready_wrapped=True;wrapped._yipman_app_ready_base=fn
            return wrapped
        setattr(api_module,name,make_wrapper(base,name));installed.append(name)
    app.state.yipman_app_ready_true_stock_hook_installed=True
    app.state.yipman_app_ready_true_stock_mutations=tuple(installed)
