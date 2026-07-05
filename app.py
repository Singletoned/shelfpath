from __future__ import annotations

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates

from booksequencer.auth import current_user, redirect_to_login, verify_supabase_token
from booksequencer.config import DEFAULT_TEMPLATE_DIR, Settings, load_settings
from booksequencer.store import Store, build_store

HTTP_SEE_OTHER = 303

templates = Jinja2Templates(directory=DEFAULT_TEMPLATE_DIR)


async def index_get(request):
    user = current_user(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    library = await request.app.state.store.load_library(user)
    return templates.TemplateResponse(request, "index.html", _context(request, library=library))


async def series_get(request):
    user = current_user(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    series_id = request.path_params["series_id"]
    sort_order = request.query_params.get("sort", "series")
    library = await request.app.state.store.load_library(user)
    series = _sorted_series(_find_series(library, series_id), sort_order)
    return templates.TemplateResponse(
        request,
        "series.html",
        _context(request, library=library, series=series, sort_order=sort_order),
    )


async def shop_get(request):
    user = current_user(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    library = await request.app.state.store.load_library(user)
    return templates.TemplateResponse(request, "shop.html", _context(request, library=library))


async def login_get(request):
    settings = request.app.state.settings
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
    if not isinstance(access_token, str) or not access_token:
        return JSONResponse({"error": "access_token is required"}, status_code=400)
    user = await verify_supabase_token(
        settings.supabase_url,
        settings.supabase_publishable_key,
        access_token,
    )
    request.session["user"] = user
    return JSONResponse({"ok": True})


async def logout_post(request):
    request.session.clear()
    return RedirectResponse("/login", status_code=HTTP_SEE_OTHER)


async def series_state_post(request):
    user = current_user(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    series_id = request.path_params["series_id"]
    form = await request.form()
    book_keys = form.getlist("book_key")
    owned_keys = set(form.getlist("owned"))
    read_keys = set(form.getlist("read"))
    await request.app.state.store.save_book_states(
        user,
        {
            book_key: {"owned": book_key in owned_keys, "read": book_key in read_keys}
            for book_key in book_keys
        },
    )
    redirect_url = request.url_for("series", series_id=series_id)
    sort_order = request.query_params.get("sort")
    if sort_order:
        redirect_url = f"{redirect_url}?sort={sort_order}"
    return RedirectResponse(redirect_url, status_code=HTTP_SEE_OTHER)


async def book_state_post(request):
    user = current_user(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    book_key = request.path_params["book_key"]
    form = await request.form()
    await request.app.state.store.save_book_state(
        user,
        book_key,
        owned="owned" in form,
        read="read" in form,
    )
    return RedirectResponse(_redirect_target(request, book_key), status_code=HTTP_SEE_OTHER)


def create_app(settings: Settings | None = None, store: Store | None = None) -> Starlette:
    resolved_settings = settings or load_settings()
    resolved_store = store or build_store(
        resolved_settings.storage,
        resolved_settings.data_dir,
        resolved_settings.supabase_url,
        resolved_settings.supabase_publishable_key,
    )
    app = Starlette(
        debug=resolved_settings.debug,
        routes=[
            Route("/", index_get, methods=("GET",), name="index"),
            Route("/login", login_get, methods=("GET",), name="login"),
            Route("/auth/callback", auth_callback_get, methods=("GET",), name="auth_callback"),
            Route("/auth/session", auth_session_post, methods=("POST",), name="auth_session"),
            Route("/logout", logout_post, methods=("POST",), name="logout"),
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
    app.add_middleware(
        SessionMiddleware,
        secret_key=resolved_settings.session_secret,
        https_only=not resolved_settings.debug,
        same_site="lax",
    )
    return app


def _context(request, **values):
    return {"request": request, "current_user": current_user(request), **values}


def _requires_auth(app: Starlette, user) -> bool:
    return app.state.settings.storage == "supabase" and user is None


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
