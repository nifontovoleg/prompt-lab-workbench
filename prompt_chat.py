"""Интерактивный CLI: выбор промпта из prompts/ → вопрос → ProxyAPI → ответ."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
DEFAULT_BASE_URL = "https://api.proxyapi.ru/openai/v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2000


def list_prompt_files() -> list[Path]:
    return sorted(PROMPTS_DIR.glob("*.json"))


def load_prompt_file(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_prompt(prompt_id: str) -> dict[str, Any]:
    path = PROMPTS_DIR / f"{prompt_id}.json"
    if not path.is_file():
        available = [p.stem for p in list_prompt_files()]
        raise FileNotFoundError(
            f"Промпт '{prompt_id}' не найден в {PROMPTS_DIR}. "
            f"Доступные: {', '.join(available) or '(пусто)'}"
        )
    return load_prompt_file(path)


def build_system_message(prompt: dict[str, Any]) -> str:
    """Собирает system-сообщение из полей JSON-промпта."""
    parts: list[str] = []

    if role := prompt.get("role"):
        parts.append(role)

    if context := prompt.get("context"):
        parts.append(f"Контекст:\n{context}")

    structure = prompt.get("structure")
    if isinstance(structure, dict):
        parts.append(f"Формат ответа: {structure.get('output_format', 'структурированный текст')}")
        components = structure.get("components") or []
        if components:
            lines = ["Структура ответа:"]
            for i, item in enumerate(components, 1):
                name = item.get("name", f"Блок {i}")
                desc = item.get("description", "")
                lines.append(f"{i}. {name}: {desc}")
            parts.append("\n".join(lines))

    fmt = prompt.get("format")
    if isinstance(fmt, dict):
        rules: list[str] = []
        for key in ("structure", "length", "style", "language", "documentation",
                    "conventions", "scalability", "prioritization", "timeline",
                    "responsibility", "deliverables"):
            if value := fmt.get(key):
                rules.append(f"- {key}: {value}")
        for req in fmt.get("requirements") or []:
            rules.append(f"- {req}")
        if rules:
            parts.append("Требования к формату:\n" + "\n".join(rules))

    tip = (prompt.get("usage_instructions") or {}).get("tip")
    if tip:
        parts.append(f"Подсказка: {tip}")

    return "\n\n".join(parts)


def get_proxy_client() -> AsyncOpenAI:
    api_key = os.getenv("PROXY_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Не задан PROXY_API_KEY. Скопируйте .env.example → .env и укажите ключ с proxyapi.ru"
        )
    base_url = os.getenv("PROXY_API_BASE_URL", DEFAULT_BASE_URL)
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


async def generate_answer(
    *,
    system: str,
    user_question: str,
    model: str,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> dict[str, Any]:
    client = get_proxy_client()
    response = await client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_question},
        ],
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Модель вернула пустой ответ")

    usage = response.usage
    return {
        "content": content.strip(),
        "model": response.model or model,
        "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
        "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
        "completion_tokens": getattr(usage, "completion_tokens", None) if usage else None,
    }


def print_request_info(result: dict[str, Any]) -> None:
    print("Информация о запросе:")
    print(f"- Модель: {result.get('model') or 'неизвестно'}")
    total = result.get("total_tokens")
    prompt_tokens = result.get("prompt_tokens")
    completion_tokens = result.get("completion_tokens")
    print(f"- Использовано токенов: {total if total is not None else 'н/д'}")
    print(f"- Промпт токены: {prompt_tokens if prompt_tokens is not None else 'н/д'}")
    print(f"- Ответ токены: {completion_tokens if completion_tokens is not None else 'н/д'}")


def print_prompt_menu(prompts: list[dict[str, Any]]) -> None:
    print("\n📋 Доступные промпты:")
    for i, item in enumerate(prompts, 1):
        name = item["data"].get("name") or item["id"]
        print(f"  {i}. {name} ({item['id']})")
    print()


def read_line(prompt: str) -> str | None:
    """Читает строку; None при EOF / Ctrl+Z."""
    try:
        return input(prompt)
    except EOFError:
        return None


def choose_prompt(prompts: list[dict[str, Any]]) -> dict[str, Any] | None:
    n = len(prompts)
    while True:
        choice_raw = read_line(
            f"1️⃣ Выберите промпт (1-{n}) или 'выход' для завершения: "
        )
        if choice_raw is None:
            return None
        choice = choice_raw.strip()
        if choice.lower() in {"выход", "exit", "q", "quit"}:
            return None
        if choice.isdigit() and 1 <= int(choice) <= n:
            selected = prompts[int(choice) - 1]
            name = selected["data"].get("name") or selected["id"]
            print(f"✅ Выбран промпт: {name}")
            return selected
        print(f"⚠️ Введите число от 1 до {n} или 'выход'.")


def ask_question(prompt_data: dict[str, Any]) -> str | None:
    test_input = (prompt_data.get("test_input") or "").strip()

    if test_input:
        print("💡 Доступен тестовый вопрос:")
        print(test_input)
        print()
        use_test_raw = read_line(
            "🧐 Использовать тестовый вопрос? (y/n, по умолчанию n): "
        )
        if use_test_raw is None:
            return None
        if use_test_raw.strip().lower() in {"y", "yes", "д", "да"}:
            return test_input

    print("✍️ Введите ваш вопрос (пустая строка — отмена):")
    question_raw = read_line("")
    if question_raw is None:
        return None
    return question_raw.strip() or None


def ask_model_settings(default_model: str) -> dict[str, Any] | None:
    """Спрашивает temperature, max_tokens и model. Enter = значение по умолчанию."""
    print("⚙️ Настройки модели:")

    while True:
        raw = read_line(
            f"🌡️ Введите temperature (0.0-1.0, по умолчанию {DEFAULT_TEMPERATURE}): "
        )
        if raw is None:
            return None
        raw = raw.strip()
        if not raw:
            temperature = DEFAULT_TEMPERATURE
            break
        try:
            temperature = float(raw.replace(",", "."))
            if 0.0 <= temperature <= 1.0:
                break
        except ValueError:
            pass
        print("⚠️ Введите число от 0.0 до 1.0.")

    while True:
        raw = read_line(
            f"🔢 Введите max_tokens (по умолчанию {DEFAULT_MAX_TOKENS}): "
        )
        if raw is None:
            return None
        raw = raw.strip()
        if not raw:
            max_tokens = DEFAULT_MAX_TOKENS
            break
        if raw.isdigit() and int(raw) > 0:
            max_tokens = int(raw)
            break
        print("⚠️ Введите целое положительное число.")

    raw = read_line(f"🤖 Введите модель (по умолчанию {default_model}): ")
    if raw is None:
        return None
    model = raw.strip() or default_model

    return {
        "temperature": temperature,
        "max_tokens": max_tokens,
        "model": model,
    }


async def interactive_loop(default_model: str) -> None:
    files = list_prompt_files()
    if not files:
        print(f"В {PROMPTS_DIR} нет JSON-промптов")
        return

    prompts = [
        {"id": path.stem, "data": load_prompt_file(path)}
        for path in files
    ]

    while True:
        print_prompt_menu(prompts)
        selected = choose_prompt(prompts)
        if selected is None:
            print("👋 До встречи!")
            return

        question = ask_question(selected["data"])
        if not question:
            print("⚠️ Вопрос не задан, возвращаемся к выбору промпта.\n")
            continue

        settings = ask_model_settings(default_model)
        if settings is None:
            print("👋 До встречи!")
            return

        system = build_system_message(selected["data"])
        print("\n⏳ Отправляем запрос к OpenAI...\n")
        try:
            result = await generate_answer(
                system=system,
                user_question=question,
                model=settings["model"],
                temperature=settings["temperature"],
                max_tokens=settings["max_tokens"],
            )
        except Exception as exc:
            print(f"❌ Ошибка API: {exc}\n")
            continue

        print("📤 Ответ:\n")
        print(result["content"])
        print()
        print_request_info(result)
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Интерактивный выбор промпта из prompts/ и генерация через ProxyAPI.",
    )
    parser.add_argument(
        "-p",
        "--prompt",
        help="ID промпта (без .json). Если не указан — интерактивный режим.",
    )
    parser.add_argument(
        "-q",
        "--question",
        help="Вопрос пользователя (для неинтерактивного режима).",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help=f"Модель (по умолчанию PROXY_API_MODEL или {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Показать доступные промпты и выйти",
    )
    return parser.parse_args()


async def main() -> None:
    load_dotenv()
    args = parse_args()
    model = args.model or os.getenv("PROXY_API_MODEL") or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)

    if args.list:
        files = list_prompt_files()
        if not files:
            print(f"В {PROMPTS_DIR} нет JSON-промптов")
            return
        for path in files:
            data = load_prompt_file(path)
            print(f"{path.stem}: {data.get('name', path.stem)}")
        return

    try:
        get_proxy_client()
    except RuntimeError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        sys.exit(1)

    # Неинтерактивный режим: -p и -q заданы явно
    if args.prompt and args.question:
        prompt = load_prompt(args.prompt)
        system = build_system_message(prompt)
        result = await generate_answer(
            system=system,
            user_question=args.question,
            model=model,
        )
        print(result["content"])
        print()
        print_request_info(result)
        return

    if args.prompt and not args.question:
        prompt = load_prompt(args.prompt)
        name = prompt.get("name") or args.prompt
        print(f"✅ Выбран промпт: {name}")
        question = ask_question(prompt)
        if not question:
            print("Ошибка: пустой вопрос пользователя", file=sys.stderr)
            sys.exit(1)
        system = build_system_message(prompt)
        result = await generate_answer(
            system=system,
            user_question=question,
            model=model,
        )
        print(result["content"])
        print()
        print_request_info(result)
        return

    await interactive_loop(model)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 До встречи!")
