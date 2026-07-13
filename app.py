from __future__ import annotations

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates

from booksequencer.ai_series import OpenAISeriesInvestigator
from booksequencer.auth import current_user, fresh_user, redirect_to_login, verify_supabase_token
from booksequencer.config import DEFAULT_TEMPLATE_DIR, Settings, load_settings
from booksequencer.store import SUGGESTION_DAILY_LIMIT, Store, build_store

HTTP_SEE_OTHER = 303

STORAGE_SUPABASE = "supabase"

ACTIVE_LIST_SESSION_KEY = "active_list_id"

templates = Jinja2Templates(directory=DEFAULT_TEMPLATE_DIR)


async def index_get(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    library = await _library_for_request(request, user)
    _remember_active_list(request, library)
    return templates.TemplateResponse(request, "index.html", _context(request, library=library))


async def series_get(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    series_id = request.path_params["series_id"]
    sort_order = request.query_params.get("sort", "series")
    library = await _library_for_request(request, user)
    _remember_active_list(request, library)
    series = _sorted_series(_find_series(library, series_id), sort_order)
    return templates.TemplateResponse(
        request,
        "series.html",
        _context(request, library=library, series=series, sort_order=sort_order),
    )


async def shop_get(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    library = await _library_for_request(request, user)
    _remember_active_list(request, library)
    return templates.TemplateResponse(request, "shop.html", _context(request, library=library))


async def lists_get(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    library = await _library_for_request(request, user)
    _remember_active_list(request, library)
    return templates.TemplateResponse(request, "lists.html", _context(request, library=library))


async def suggest_get(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    allowed = await request.app.state.store.can_suggest_series(user)
    remaining = 0
    if allowed:
        remaining = max(
            0, SUGGESTION_DAILY_LIMIT - await request.app.state.store.suggestion_count_today(user)
        )
    return templates.TemplateResponse(
        request,
        "suggest.html",
        _context(request, allowed=allowed, remaining=remaining, suggestion=None),
    )


async def suggest_post(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    if not await request.app.state.store.can_suggest_series(user):
        return templates.TemplateResponse(
            request,
            "suggest.html",
            _context(request, allowed=False, remaining=0, suggestion=None),
            status_code=403,
        )
    remaining = SUGGESTION_DAILY_LIMIT - await request.app.state.store.suggestion_count_today(user)
    if remaining <= 0:
        return templates.TemplateResponse(
            request,
            "suggest.html",
            _context(request, allowed=True, remaining=0, suggestion=None, rate_limited=True),
            status_code=429,
        )
    form = await request.form()
    prompt = form.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt is required.")
    try:
        proposal = await request.app.state.ai_series_investigator.investigate(prompt)
    except Exception as error:
        suggestion = await request.app.state.store.create_series_suggestion(
            user, prompt.strip(), "failed", error=str(error)
        )
        return templates.TemplateResponse(
            request,
            "suggest_detail.html",
            _context(request, suggestion=suggestion),
            status_code=500,
        )
    suggestion = await request.app.state.store.create_series_suggestion(
        user, prompt.strip(), "submitted", proposal=proposal.to_dict()
    )
    return RedirectResponse(
        request.url_for("suggest_detail", suggestion_id=suggestion["id"]),
        status_code=HTTP_SEE_OTHER,
    )


async def suggest_detail_get(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    suggestion = await request.app.state.store.get_series_suggestion(
        user, request.path_params["suggestion_id"]
    )
    return templates.TemplateResponse(
        request,
        "suggest_detail.html",
        _context(request, suggestion=suggestion),
    )


async def suggest_approve_post(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    await request.app.state.store.approve_series_suggestion(
        user, request.path_params["suggestion_id"]
    )
    return RedirectResponse(
        request.url_for("suggest_detail", suggestion_id=request.path_params["suggestion_id"]),
        status_code=HTTP_SEE_OTHER,
    )


async def suggest_reject_post(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    await request.app.state.store.reject_series_suggestion(
        user, request.path_params["suggestion_id"]
    )
    return RedirectResponse(
        request.url_for("suggest_detail", suggestion_id=request.path_params["suggestion_id"]),
        status_code=HTTP_SEE_OTHER,
    )


async def list_select_post(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    form = await request.form()
    list_id = form.get("list_id")
    if not isinstance(list_id, str) or not list_id:
        raise ValueError("list_id is required.")
    accessible_lists = await request.app.state.store.list_lists(user)
    if list_id not in {book_list["id"] for book_list in accessible_lists}:
        raise ValueError(f"Unknown or inaccessible list id: {list_id}")
    request.session[ACTIVE_LIST_SESSION_KEY] = list_id
    return RedirectResponse(_safe_next(form.get("next")), status_code=HTTP_SEE_OTHER)


async def list_share_post(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    form = await request.form()
    list_id = form.get("list_id")
    email = form.get("email")
    role = form.get("role", "editor")
    if not isinstance(list_id, str) or not list_id:
        raise ValueError("list_id is required.")
    if not isinstance(email, str):
        raise ValueError("email is required.")
    if not isinstance(role, str):
        raise ValueError("role is required.")
    await request.app.state.store.share_list(user, list_id, email, role)
    request.session[ACTIVE_LIST_SESSION_KEY] = list_id
    return RedirectResponse("/lists", status_code=HTTP_SEE_OTHER)


async def login_get(request):
    settings = request.app.state.settings
    if settings.local_auth_email and settings.debug and settings.storage == STORAGE_SUPABASE:
        request.session["user"] = await request.app.state.store.local_test_user(
            settings.local_auth_email
        )
        return RedirectResponse(
            _safe_next(request.query_params.get("next", "/")), status_code=HTTP_SEE_OTHER
        )
    return templates.TemplateResponse(
        request,
        "login.html",
        _context(
            request,
            next_url=request.query_params.get("next", "/"),
            supabase_url=settings.supabase_url,
            supabase_publishable_key=settings.supabase_publishable_key,
        ),
    )


async def auth_callback_get(request):
    settings = request.app.state.settings
    return templates.TemplateResponse(
        request,
        "auth_callback.html",
        _context(
            request,
            supabase_url=settings.supabase_url,
            supabase_publishable_key=settings.supabase_publishable_key,
        ),
    )


async def auth_session_post(request):
    settings = request.app.state.settings
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise ValueError("Supabase auth requires SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY.")
    payload = await request.json()
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    expires_at = payload.get("expires_at")
    if not isinstance(access_token, str) or not access_token:
        return JSONResponse({"error": "access_token is required"}, status_code=400)
    if not isinstance(refresh_token, str) or not refresh_token:
        return JSONResponse({"error": "refresh_token is required"}, status_code=400)
    user = await verify_supabase_token(
        settings.supabase_url,
        settings.supabase_publishable_key,
        access_token,
        refresh_token,
        expires_at if isinstance(expires_at, int) else None,
    )
    request.session["user"] = user
    return JSONResponse({"ok": True})


async def logout_post(request):
    request.session.clear()
    return RedirectResponse("/login", status_code=HTTP_SEE_OTHER)


async def series_state_post(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    series_id = request.path_params["series_id"]
    form = await request.form()
    book_keys = form.getlist("book_key")
    owned_keys = set(form.getlist("owned"))
    read_keys = set(form.getlist("read"))
    wanted_keys = set(form.getlist("wanted"))
    await request.app.state.store.save_book_states(
        user,
        {
            book_key: {
                "owned": book_key in owned_keys,
                "read": book_key in read_keys,
                "wanted": book_key in wanted_keys,
            }
            for book_key in book_keys
        },
        _active_list_id(request),
    )
    redirect_url = request.url_for("series", series_id=series_id)
    sort_order = request.query_params.get("sort")
    if sort_order:
        redirect_url = f"{redirect_url}?sort={sort_order}"
    return RedirectResponse(redirect_url, status_code=HTTP_SEE_OTHER)


async def book_state_post(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    book_key = request.path_params["book_key"]
    form = await request.form()
    await request.app.state.store.save_book_state(
        user,
        book_key,
        owned="owned" in form,
        read="read" in form,
        wanted="wanted" in form,
        list_id=_active_list_id(request),
    )
    return RedirectResponse(_redirect_target(request, book_key), status_code=HTTP_SEE_OTHER)


def create_app(
    settings: Settings | None = None,
    store: Store | None = None,
    ai_series_investigator=None,
) -> Starlette:
    resolved_settings = settings or load_settings()
    resolved_store = store or build_store(
        resolved_settings.storage,
        resolved_settings.data_dir,
        resolved_settings.supabase_url,
        resolved_settings.supabase_publishable_key,
        resolved_settings.supabase_service_role_key,
    )
    app = Starlette(
        debug=resolved_settings.debug,
        routes=[
            Route("/", index_get, methods=("GET",), name="index"),
            Route("/login", login_get, methods=("GET",), name="login"),
            Route("/auth/callback", auth_callback_get, methods=("GET",), name="auth_callback"),
            Route("/auth/session", auth_session_post, methods=("POST",), name="auth_session"),
            Route("/logout", logout_post, methods=("POST",), name="logout"),
            Route("/lists", lists_get, methods=("GET",), name="lists"),
            Route("/lists/select", list_select_post, methods=("POST",), name="list_select"),
            Route("/lists/share", list_share_post, methods=("POST",), name="list_share"),
            Route("/suggest", suggest_get, methods=("GET",), name="suggest"),
            Route("/suggest", suggest_post, methods=("POST",), name="suggest_post"),
            Route(
                "/suggest/{suggestion_id}",
                suggest_detail_get,
                methods=("GET",),
                name="suggest_detail",
            ),
            Route(
                "/suggest/{suggestion_id}/approve",
                suggest_approve_post,
                methods=("POST",),
                name="suggest_approve",
            ),
            Route(
                "/suggest/{suggestion_id}/reject",
                suggest_reject_post,
                methods=("POST",),
                name="suggest_reject",
            ),
            Route("/series/{series_id}", series_get, methods=("GET",), name="series"),
            Route(
                "/series/{series_id}/state",
                series_state_post,
                methods=("POST",),
                name="series_state",
            ),
            Route("/shop", shop_get, methods=("GET",), name="shop"),
            Route(
                "/books/{book_key:path}/state",
                book_state_post,
                methods=("POST",),
                name="book_state",
            ),
        ],
    )
    app.state.settings = resolved_settings
    app.state.store = resolved_store
    app.state.ai_series_investigator = ai_series_investigator or OpenAISeriesInvestigator(
        resolved_settings.openai_api_key,
        resolved_settings.openai_model,
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=resolved_settings.session_secret,
        https_only=not resolved_settings.debug,
        same_site="lax",
    )
    return app


async def _user_for_request(request):
    settings = request.app.state.settings
    if settings.storage != STORAGE_SUPABASE:
        return current_user(request)
    return await fresh_user(
        request,
        settings.supabase_url,
        settings.supabase_publishable_key,
    )


async def _library_for_request(request, user):
    return await request.app.state.store.load_library(user, _active_list_id(request))


def _active_list_id(request) -> str | None:
    value = request.session.get(ACTIVE_LIST_SESSION_KEY)
    if isinstance(value, str):
        return value
    return None


def _remember_active_list(request, library) -> None:
    current_list = library.get("current_list")
    if isinstance(current_list, dict) and isinstance(current_list.get("id"), str):
        request.session[ACTIVE_LIST_SESSION_KEY] = current_list["id"]


def _safe_next(value) -> str:
    if isinstance(value, str) and value.startswith("/") and not value.startswith("//"):
        return value
    return "/"


def _context(request, **values):
    return {"request": request, "current_user": current_user(request), **values}


def _requires_auth(app: Starlette, user) -> bool:
    return app.state.settings.storage == STORAGE_SUPABASE and user is None


def _find_series(library, series_id):
    for series in library["series"]:
        if series["id"] == series_id:
            return series
    raise ValueError(f"Unknown series id: {series_id}")


def _sorted_series(series, sort_order):
    if sort_order not in {"series", "title"}:
        raise ValueError(f"Unknown series sort order: {sort_order}")
    books = list(series["books"])
    if sort_order == "title":
        books.sort(key=lambda book: _sort_title(book["title"]))
    return {**series, "books": books}


def _sort_title(title):
    lowered = title.casefold()
    for article in ("the ", "a ", "an "):
        if lowered.startswith(article):
            return lowered[len(article) :]
    return lowered


def _redirect_target(request, book_key):
    target = request.query_params.get("next")
    if target:
        return target
    series_id = book_key.split("/", maxsplit=1)[0]
    return request.url_for("series", series_id=series_id)


app = create_app()
