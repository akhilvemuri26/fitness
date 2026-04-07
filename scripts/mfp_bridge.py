from __future__ import annotations

import argparse
import os
from datetime import date, timedelta
from http.cookiejar import CookieJar, MozillaCookieJar
from pathlib import Path

import httpx

COOKIE_DOMAINS = [
    "myfitnesspal.com",
    "www.myfitnesspal.com",
]
DEFAULT_BROWSER_ORDER = ["chrome", "chromium", "edge", "firefox", "safari"]
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def env_default(key: str, fallback: str | None = None) -> str | None:
    value = os.getenv(key)
    if value is not None:
        return value
    if ENV_PATH.exists():
        for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            env_key, env_value = line.split("=", 1)
            if env_key.strip() == key:
                return env_value.strip().strip('"').strip("'")
    return fallback


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Push MyFitnessPal data into Fitness Hub")
    parser.add_argument("--days", type=int, default=int(env_default("MFP_BACKFILL_DAYS", "90") or "90"))
    parser.add_argument(
        "--base-url",
        default=env_default("MFP_BRIDGE_BASE_URL", "http://127.0.0.1:8000"),
    )
    parser.add_argument(
        "--token",
        default=env_default("MFP_BRIDGE_SHARED_TOKEN", "change-me"),
    )
    parser.add_argument(
        "--browser",
        default=env_default("MFP_BROWSER", "auto"),
        help="Browser cookie source to use: auto, chrome, chromium, edge, firefox, or safari",
    )
    parser.add_argument(
        "--cookie-file",
        default=env_default("MFP_COOKIE_FILE"),
        help="Optional Netscape-format cookies.txt export for myfitnesspal.com",
    )
    parser.add_argument(
        "--cookie-header",
        default=env_default("MFP_COOKIE_HEADER"),
        help="Optional raw Cookie header copied from a logged-in myfitnesspal.com browser request",
    )
    return parser.parse_args()


def daterange(days: int) -> list[date]:
    today = date.today()
    return [today - timedelta(days=offset) for offset in range(days)]


def build_payload(
    days: int,
    browser_name: str,
    cookie_file: str | None = None,
    cookie_header: str | None = None,
) -> dict:
    try:
        import myfitnesspal
        import browser_cookie3
    except ImportError as exc:
        raise SystemExit(
            "python-myfitnesspal is not installed. Run: python3 -m pip install -e '.[mfp]'"
        ) from exc

    client = myfitnesspal.Client(
        cookiejar=build_cookie_jar(
            browser_cookie3,
            browser_name,
            cookie_file=cookie_file,
            cookie_header=cookie_header,
        )
    )
    all_dates = daterange(days)
    lower = min(all_dates)
    upper = max(all_dates)
    weights = client.get_measurements("Weight", lower_bound=lower, upper_bound=upper)

    items = []
    for target_date in all_dates:
        day = client.get_date(target_date)
        totals = day.totals
        meals = []
        for meal in day.meals:
            for entry in meal.entries:
                meals.append(
                    {
                        "meal_name": meal.name,
                        "food_name": entry.short_name or entry.name,
                        "serving_size": (
                            f"{entry.quantity or ''} {entry.unit or ''}".strip() or None
                        ),
                        "calories": entry.nutrition_information.get("calories"),
                        "protein_g": entry.nutrition_information.get("protein"),
                        "carbs_g": entry.nutrition_information.get("carbohydrates"),
                        "fat_g": entry.nutrition_information.get("fat"),
                        "nutrition_json": dict(entry.nutrition_information),
                    }
                )

        weight_entries = []
        if target_date in weights:
            weight_entries.append({"value": float(weights[target_date]), "unit": "pounds"})

        items.append(
            {
                "entry_date": target_date.isoformat(),
                "calories": totals.get("calories"),
                "protein_g": totals.get("protein"),
                "carbs_g": totals.get("carbohydrates"),
                "fat_g": totals.get("fat"),
                "sugar_g": totals.get("sugar"),
                "fiber_g": totals.get("fiber"),
                "water_ml": float(day.water or 0),
                "notes": str(day.notes or ""),
                "raw_payload": {
                    "meal_count": len(day.meals),
                    "entry_count": len(list(day.entries)),
                },
                "meals": meals,
                "weight_entries": weight_entries,
            }
        )

    return {"days": items}


def build_cookie_jar(
    browser_cookie3_module,
    browser_name: str,
    *,
    cookie_file: str | None = None,
    cookie_header: str | None = None,
) -> CookieJar:
    if cookie_header:
        return parse_cookie_header(cookie_header)
    if cookie_file:
        return load_cookie_file(cookie_file)

    order = DEFAULT_BROWSER_ORDER if browser_name == "auto" else [browser_name]
    attempts: list[str] = []
    for candidate in order:
        loader = getattr(browser_cookie3_module, candidate, None)
        if loader is None:
            attempts.append(f"{candidate}: unavailable")
            continue
        try:
            jar = CookieJar()
            loaded_any = False
            for domain in COOKIE_DOMAINS:
                for cookie in loader(domain_name=domain):
                    jar.set_cookie(cookie)
                    loaded_any = True
            if loaded_any:
                return jar
            attempts.append(f"{candidate}: no MyFitnessPal cookies found")
        except PermissionError as exc:
            attempts.append(f"{candidate}: permission denied ({exc})")
        except Exception as exc:  # pragma: no cover - depends on local browser state
            attempts.append(f"{candidate}: {exc}")
    attempted = "; ".join(attempts) if attempts else "no browsers attempted"
    raise SystemExit(
        "Unable to load MyFitnessPal browser cookies. "
        "Try logging into MyFitnessPal in Chrome or Firefox first, then rerun "
        "`python3 scripts/mfp_bridge.py --browser chrome --days 90`, or pass "
        "`--cookie-file` / `--cookie-header` to bypass browser access. "
        f"Attempt details: {attempted}"
    )


def load_cookie_file(cookie_file: str) -> CookieJar:
    path = Path(cookie_file).expanduser()
    if not path.exists():
        raise SystemExit(f"Cookie file not found: {path}")
    jar = MozillaCookieJar(str(path))
    jar.load(ignore_discard=True, ignore_expires=True)
    return jar


def parse_cookie_header(cookie_header: str) -> CookieJar:
    from requests.cookies import RequestsCookieJar, create_cookie

    jar = RequestsCookieJar()
    for part in cookie_header.split(";"):
        item = part.strip()
        if not item or "=" not in item:
            continue
        name, value = item.split("=", 1)
        jar.set_cookie(
            create_cookie(
                name=name.strip(),
                value=value.strip(),
                domain=".myfitnesspal.com",
                path="/",
            )
        )
    if not jar:
        raise SystemExit("No valid cookies were found in --cookie-header.")
    return jar


def main() -> None:
    args = parse_args()
    payload = build_payload(
        args.days,
        args.browser,
        cookie_file=args.cookie_file,
        cookie_header=args.cookie_header,
    )
    response = httpx.post(
        f"{args.base_url.rstrip('/')}/internal/mfp-sync-batch",
        json=payload,
        headers={"X-MFP-Bridge-Token": args.token},
        timeout=120.0,
    )
    if response.status_code == 401:
        raise SystemExit(
            "The local bridge reached Fitness Hub, but the MFP bridge token was rejected. "
            "Make sure `MFP_BRIDGE_SHARED_TOKEN` in `.env` matches the running app, or pass "
            "`--token <your-token>` explicitly."
        )
    response.raise_for_status()
    print(response.json())


if __name__ == "__main__":
    main()
