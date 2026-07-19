from __future__ import annotations

import re
from difflib import SequenceMatcher
from urllib.parse import quote

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from booksequencer.ai_series import OpenAISeriesInvestigator
from booksequencer.auth import current_user, fresh_user, redirect_to_login, verify_supabase_token
from booksequencer.config import DEFAULT_TEMPLATE_DIR, Settings, load_settings
from booksequencer.covers import COVER_ROOT, STATIC_ROOT
from booksequencer.email import InvitationEmailSender
from booksequencer.invitations import (
    InvitationTokenError,
    create_invitation_token,
    verify_invitation_token,
)
from booksequencer.store import SUGGESTION_DAILY_LIMIT, Store, build_store

HTTP_SEE_OTHER = 303
MAX_SHOP_MATCHES = 12
SEARCH_STOP_WORDS = frozenset({"a", "an", "and", "of", "the", "to"})

STORAGE_SUPABASE = "supabase"

ACTIVE_LIST_SESSION_KEY = "active_list_id"
LOCAL_AUTH_SIGNED_OUT_SESSION_KEY = "local_auth_signed_out"

templates = Jinja2Templates(directory=DEFAULT_TEMPLATE_DIR)


async def health_get(request):
    return JSONResponse({"status": "ok"})


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
    filter_mode = request.query_params.get("filter", "all")
    library = await _library_for_request(request, user)
    _remember_active_list(request, library)
    series = _filtered_series(
        _sorted_series(_find_series(library, series_id), sort_order), filter_mode
    )
    return templates.TemplateResponse(
        request,
        "series.html",
        _context(
            request,
            library=library,
            series=series,
            sort_order=sort_order,
            filter_mode=filter_mode,
        ),
    )


async def shop_get(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    library = await _library_for_request(request, user)
    _remember_active_list(request, library)
    search_query = _clean_search_query(request.query_params.get("q", ""))
    shop_matches = _shop_matches(library, search_query) if search_query else []
    return templates.TemplateResponse(
        request,
        "shop.html",
        _context(
            request,
            library=library,
            search_query=search_query,
            shop_matches=shop_matches,
        ),
    )


async def lists_get(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    library = await _library_for_request(request, user)
    _remember_active_list(request, library)
    return templates.TemplateResponse(
        request,
        "lists.html",
        _context(request, library=library, joined=request.query_params.get("joined")),
    )


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


async def list_people_get(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    people = await request.app.state.store.get_list_people(user, request.path_params["list_id"])
    return templates.TemplateResponse(
        request,
        "list_people.html",
        _context(request, people=people, invited=request.query_params.get("invited")),
    )


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
    if not isinstance(email, str) or not email.strip():
        raise ValueError("email is required.")
    if not isinstance(role, str):
        raise ValueError("role is required.")
    sender = request.app.state.invitation_email_sender
    secret = request.app.state.settings.invitation_token_secret
    if sender is None:
        raise ValueError("SHELFPATH_SMTP_HOST must be configured before sending invitations.")
    if secret is None:
        raise ValueError(
            "SHELFPATH_INVITATION_TOKEN_SECRET must be configured before sending invitations."
        )
    people = await request.app.state.store.get_list_people(user, list_id)
    normalized_email = email.strip().lower()
    token = create_invitation_token(list_id, normalized_email, role, secret)
    invitation_url = _invitation_url(request.app.state.settings.public_url, list_id, role, token)
    await sender.send_list_invitation(
        normalized_email, people["list"]["name"], role, invitation_url
    )
    request.session[ACTIVE_LIST_SESSION_KEY] = list_id
    return RedirectResponse(
        f"/lists/{list_id}/people?invited={quote(normalized_email)}",
        status_code=HTTP_SEE_OTHER,
    )


async def invitation_get(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    email = user.get("email") if isinstance(user, dict) else None
    secret = request.app.state.settings.invitation_token_secret
    if not isinstance(email, str) or secret is None:
        return _invitation_error(request, "This invitation link is no longer valid.")
    list_id = request.path_params["list_id"]
    role = request.path_params["role"]
    token = request.path_params["token"]
    try:
        verify_invitation_token(list_id, email, role, token, secret)
    except InvitationTokenError as error:
        return _invitation_error(request, str(error))
    await request.app.state.store.accept_list_invitation(user, list_id, role)
    request.session[ACTIVE_LIST_SESSION_KEY] = list_id
    return RedirectResponse(f"/lists?joined={quote(list_id)}", status_code=HTTP_SEE_OTHER)


async def list_person_update_post(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    form = await request.form()
    list_id = form.get("list_id")
    email = form.get("email")
    role = form.get("role")
    if not isinstance(list_id, str) or not isinstance(email, str) or not isinstance(role, str):
        raise ValueError("list_id, email, and role are required.")
    await request.app.state.store.update_list_person_role(user, list_id, email, role)
    return RedirectResponse(f"/lists/{list_id}/people", status_code=HTTP_SEE_OTHER)


async def list_person_remove_post(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    form = await request.form()
    list_id = form.get("list_id")
    email = form.get("email")
    if not isinstance(list_id, str) or not isinstance(email, str):
        raise ValueError("list_id and email are required.")
    await request.app.state.store.remove_list_person(user, list_id, email)
    return RedirectResponse(f"/lists/{list_id}/people", status_code=HTTP_SEE_OTHER)


async def login_get(request):
    settings = request.app.state.settings
    local_auth_enabled = _local_auth_enabled(settings)
    if local_auth_enabled and not request.session.get(LOCAL_AUTH_SIGNED_OUT_SESSION_KEY):
        await _sign_in_local_test_user(request)
        return RedirectResponse(
            _safe_next(request.query_params.get("next", "/")), status_code=HTTP_SEE_OTHER
        )
    return templates.TemplateResponse(
        request,
        "login.html",
        _context(
            request,
            local_auth_enabled=local_auth_enabled,
            next_url=_safe_next(request.query_params.get("next", "/")),
            supabase_url=settings.supabase_url,
            supabase_publishable_key=settings.supabase_publishable_key,
        ),
    )


async def local_login_post(request):
    if not _local_auth_enabled(request.app.state.settings):
        return RedirectResponse("/login", status_code=HTTP_SEE_OTHER)
    form = await request.form()
    await _sign_in_local_test_user(request)
    return RedirectResponse(_safe_next(form.get("next")), status_code=HTTP_SEE_OTHER)


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
    local_auth_enabled = _local_auth_enabled(request.app.state.settings)
    request.session.clear()
    if local_auth_enabled:
        request.session[LOCAL_AUTH_SIGNED_OUT_SESSION_KEY] = True
        return RedirectResponse("/login?local_signed_out=1", status_code=HTTP_SEE_OTHER)
    return RedirectResponse("/login", status_code=HTTP_SEE_OTHER)


async def series_state_post(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    series_id = request.path_params["series_id"]
    await _require_active_list_editor(request, user)
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
    query_params = []
    sort_order = request.query_params.get("sort")
    if sort_order:
        query_params.append(f"sort={sort_order}")
    filter_mode = request.query_params.get("filter")
    if filter_mode:
        query_params.append(f"filter={filter_mode}")
    if query_params:
        redirect_url = f"{redirect_url}?{'&'.join(query_params)}"
    return RedirectResponse(redirect_url, status_code=HTTP_SEE_OTHER)


async def book_state_post(request):
    user = await _user_for_request(request)
    if _requires_auth(request.app, user):
        return redirect_to_login(request)
    book_key = request.path_params["book_key"]
    await _require_active_list_editor(request, user)
    form = await request.form()
    await request.app.state.store.save_book_state(
        user,
        book_key,
        owned="owned" in form,
        read="read" in form,
        wanted="wanted" in form,
        list_id=_active_list_id(request),
    )
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"saved": True})
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
            Route("/health", health_get, methods=("GET",), name="health"),
            Route("/", index_get, methods=("GET",), name="index"),
            Route("/login", login_get, methods=("GET",), name="login"),
            Route("/login/local", local_login_post, methods=("POST",), name="local_login"),
            Route("/auth/callback", auth_callback_get, methods=("GET",), name="auth_callback"),
            Route("/auth/session", auth_session_post, methods=("POST",), name="auth_session"),
            Route("/logout", logout_post, methods=("POST",), name="logout"),
            Route("/lists", lists_get, methods=("GET",), name="lists"),
            Route("/lists/select", list_select_post, methods=("POST",), name="list_select"),
            Route("/lists/share", list_share_post, methods=("POST",), name="list_share"),
            Route(
                "/invite/{list_id}/{role}/{token}",
                invitation_get,
                methods=("GET",),
                name="invitation",
            ),
            Route("/lists/{list_id}/people", list_people_get, methods=("GET",), name="list_people"),
            Route(
                "/lists/{list_id}/people/update",
                list_person_update_post,
                methods=("POST",),
                name="list_person_update",
            ),
            Route(
                "/lists/{list_id}/people/remove",
                list_person_remove_post,
                methods=("POST",),
                name="list_person_remove",
            ),
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
            Mount("/covers", StaticFiles(directory=COVER_ROOT, check_dir=False), name="covers"),
            Mount("/static", StaticFiles(directory=STATIC_ROOT, check_dir=False), name="static"),
        ],
    )
    app.state.settings = resolved_settings
    app.state.store = resolved_store
    app.state.invitation_email_sender = _invitation_email_sender(resolved_settings)
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
    if _local_auth_enabled(settings) and not request.session.get(LOCAL_AUTH_SIGNED_OUT_SESSION_KEY):
        return await _sign_in_local_test_user(request)
    return await fresh_user(
        request,
        settings.supabase_url,
        settings.supabase_publishable_key,
    )


def _invitation_email_sender(settings: Settings) -> InvitationEmailSender | None:
    if settings.smtp_host is None:
        return None
    return InvitationEmailSender(
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_username,
        settings.smtp_password,
        settings.mail_from,
    )


def _local_auth_enabled(settings: Settings) -> bool:
    return bool(
        settings.debug and settings.local_auth_email and settings.storage == STORAGE_SUPABASE
    )


async def _sign_in_local_test_user(request):
    settings = request.app.state.settings
    previous_user = current_user(request)
    user = await request.app.state.store.local_test_user(
        settings.local_auth_email, settings.local_auth_password
    )
    if previous_user is None or previous_user.get("id") != user["id"]:
        request.session.pop(ACTIVE_LIST_SESSION_KEY, None)
    request.session.pop(LOCAL_AUTH_SIGNED_OUT_SESSION_KEY, None)
    request.session["user"] = user
    return user


async def _library_for_request(request, user):
    return await request.app.state.store.load_library(user, _active_list_id(request))


def _active_list_id(request) -> str | None:
    value = request.session.get(ACTIVE_LIST_SESSION_KEY)
    if isinstance(value, str):
        return value
    return None


async def _require_active_list_editor(request, user) -> None:
    active_list_id = _active_list_id(request)
    lists = await request.app.state.store.list_lists(user)
    active_list = _select_active_list(lists, active_list_id)
    if active_list["role"] not in {"owner", "editor"}:
        raise PermissionError("View-only list members cannot update book status.")


def _select_active_list(lists, active_list_id):
    if active_list_id:
        for book_list in lists:
            if book_list["id"] == active_list_id:
                return book_list
    if not lists:
        raise ValueError("User has no accessible lists.")
    return lists[0]


def _remember_active_list(request, library) -> None:
    current_list = library.get("current_list")
    if isinstance(current_list, dict) and isinstance(current_list.get("id"), str):
        request.session[ACTIVE_LIST_SESSION_KEY] = current_list["id"]


def _invitation_url(public_url: str, list_id: str, role: str, token: str) -> str:
    return f"{public_url.rstrip('/')}/invite/{quote(list_id)}/{quote(role)}/{quote(token)}"


def _invitation_error(request, message: str):
    return templates.TemplateResponse(
        request, "invitation_error.html", _context(request, message=message), status_code=400
    )


def _safe_next(value) -> str:
    if isinstance(value, str) and value.startswith("/") and not value.startswith("//"):
        return value
    return "/"


def _context(request, **values):
    return {
        "request": request,
        "current_user": current_user(request),
        "nav_section": _nav_section(request),
        **values,
    }


def _nav_section(request) -> str:
    path = request.url.path
    if path == "/" or path.startswith("/series/"):
        return "shelf"
    if path == "/shop":
        return "shop"
    if path == "/lists":
        return "lists"
    if path == "/suggest":
        return "suggest"
    return ""


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


def _filtered_series(series, filter_mode):
    if filter_mode == "all":
        return series
    if filter_mode == "wanted":
        books = [book for book in series["books"] if book["wanted"] and not book["owned"]]
    elif filter_mode == "owned":
        books = [book for book in series["books"] if book["owned"]]
    else:
        raise ValueError(f"Unknown series filter: {filter_mode}")
    return {**series, "books": books}


def _clean_search_query(value):
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _shop_matches(library, search_query):
    matches = []
    for series in library["series"]:
        for book in series["books"]:
            score = _match_score(search_query, book, series)
            if score is None:
                continue
            matches.append(
                {
                    "book": book,
                    "series": series,
                    "score": score,
                    "verdict": _shop_verdict(book),
                }
            )
    matches.sort(key=lambda match: (-match["score"], match["book"]["position"]))
    return matches[:MAX_SHOP_MATCHES]


def _match_score(search_query, book, series):
    query = _search_terms(search_query)
    title = _search_terms(book["title"])
    if not query or not title:
        return None
    if query in title:
        return 1.0
    query_tokens = set(query.split())
    candidate = " ".join(
        value
        for value in (book["title"], book.get("author"), series["title"], series.get("author"))
        if value
    )
    candidate_tokens = set(_search_terms(candidate).split())
    overlap = len(query_tokens & candidate_tokens) / len(query_tokens)
    similarity = SequenceMatcher(None, query, title).ratio()
    score = overlap * 0.75 + similarity * 0.25
    if score < 0.45:
        return None
    return score


def _search_terms(value):
    return " ".join(
        term for term in re.findall(r"[\w]+", value.casefold()) if term not in SEARCH_STOP_WORDS
    )


def _shop_verdict(book):
    if book["owned"]:
        return "owned"
    if book["wanted"]:
        return "wanted"
    return "not-wanted"


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
