from __future__ import annotations
"""Refresh App Ready intelligence after authoritative True Stock mutations."""
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
                result=fn(*args,**kwargs)
                family=_family_hint(args,kwargs,result)
                invalidate=getattr(api_module,'backoffice_invalidate_true_stock_dependent_caches',None)
                if callable(invalidate):
                    try:invalidate(family)
                    except TypeError:
                        try:invalidate()
                        except Exception:pass
                    except Exception:pass
                overlay_applied=False
                if isinstance(result,dict):
                    try:
                        from yipman_app_ready_true_stock_overlay import apply_true_stock_family_overlay
                        overlay=apply_true_stock_family_overlay(result)
                        overlay_applied=overlay.get('status')=='APP_READY'
                        result['app_ready_incremental_refresh']=overlay
                    except Exception as exc:
                        result['app_ready_incremental_refresh']={'status':'FAILED','error':type(exc).__name__}
                # Global rebuild is now fallback-only. Normal submit and cancel
                # paths both publish a family-scoped durable generation.
                if not overlay_applied:
                    try:request_rebuild(source_batch_id='TRUE_STOCK_FALLBACK:'+fn_name+':'+(family or 'UNKNOWN'))
                    except Exception:pass
                return result
            wrapped._yipman_app_ready_wrapped=True;wrapped._yipman_app_ready_base=fn
            return wrapped
        setattr(api_module,name,make_wrapper(base,name));installed.append(name)
    app.state.yipman_app_ready_true_stock_hook_installed=True
    app.state.yipman_app_ready_true_stock_mutations=tuple(installed)
