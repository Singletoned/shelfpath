from __future__ import annotations

import pathlib

from starlette.applications import Starlette
from starlette.responses import RedirectResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates

from booksequencer.library import load_library, save_book_state, save_book_states

PROJECT_DIR = pathlib.Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
HTTP_SEE_OTHER = 303

templates = Jinja2Templates(directory="templates")


async def index_get(request):
    library = load_library(DATA_DIR)
    return templates.TemplateResponse(request, "index.html", {"library": library})


async def series_get(request):
    series_id = request.path_params["series_id"]
    library = load_library(DATA_DIR)
    series = _find_series(library, series_id)
    return templates.TemplateResponse(
        request,
        "series.html",
        {"library": library, "series": series},
    )


async def shop_get(request):
    library = load_library(DATA_DIR)
    return templates.TemplateResponse(request, "shop.html", {"library": library})


async def series_state_post(request):
    series_id = request.path_params["series_id"]
    form = await request.form()
    book_keys = form.getlist("book_key")
    owned_keys = set(form.getlist("owned"))
    read_keys = set(form.getlist("read"))
    save_book_states(
        DATA_DIR,
        {
            book_key: {"owned": book_key in owned_keys, "read": book_key in read_keys}
            for book_key in book_keys
        },
    )
    return RedirectResponse(
        request.url_for("series", series_id=series_id), status_code=HTTP_SEE_OTHER
    )


async def book_state_post(request):
    book_key = request.path_params["book_key"]
    form = await request.form()
    save_book_state(
        DATA_DIR,
        book_key,
        owned="owned" in form,
        read="read" in form,
    )
    return RedirectResponse(_redirect_target(request, book_key), status_code=HTTP_SEE_OTHER)


def _find_series(library, series_id):
    for series in library["series"]:
        if series["id"] == series_id:
            return series
    raise ValueError(f"Unknown series id: {series_id}")


def _redirect_target(request, book_key):
    target = request.query_params.get("next")
    if target:
        return target
    series_id = book_key.split("/", maxsplit=1)[0]
    return request.url_for("series", series_id=series_id)


app = Starlette(
    debug=True,
    routes=[
        Route("/", index_get, methods=("GET",), name="index"),
        Route("/series/{series_id}", series_get, methods=("GET",), name="series"),
        Route(
            "/series/{series_id}/state",
            series_state_post,
            methods=("POST",),
            name="series_state",
        ),
        Route("/shop", shop_get, methods=("GET",), name="shop"),
        Route(
            "/books/{book_key:path}/state", book_state_post, methods=("POST",), name="book_state"
        ),
    ],
)
