"""A fake `claude -p --output-format stream-json` for tests (copied into an executable).

The backend passes the CLI a minimal environment on purpose, so this fake reads its
settings from files next to it:
- `root.txt`: the backend folder, to import tests.fake_llm;
- `mode`: `limit` or `auth` answers the CLI's error instead.
Every call appends what it saw (arguments, names of environment variables, stdin) as one
line of `cli.jsonl` next to it.

Grading (prompts/grade.md as system prompt): a valid tagged grading for the rubric found
in the message, streamed as text deltas. Generation (prompts/generate.md): with
`--tools WebSearch`, one search whose result carries SEARCH_URL, then the exercise JSON.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.insert(0, open(os.path.join(HERE, "root.txt")).read().strip())
from tests.fake_llm import SEARCH_URL, exercise_json, grade_text  # noqa: E402


def emit(event):
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else ""


message = sys.stdin.read()
with open(os.path.join(HERE, "cli.jsonl"), "a") as log:
    log.write(
        json.dumps({"argv": sys.argv[1:], "env": sorted(os.environ), "stdin": message}) + "\n"
    )
mode_file = os.path.join(HERE, "mode")
mode = open(mode_file).read().strip() if os.path.exists(mode_file) else "ok"

emit({"type": "system", "subtype": "init", "model": "claude-sonnet-5-5", "tools": []})
if mode in ("limit", "auth"):
    error = {
        "limit": "You've hit your usage limit · resets 3pm",
        "auth": "Invalid API key · Please run /login",
    }[mode]
    emit({"type": "result", "subtype": "success", "is_error": True, "result": error})
    sys.exit(1)

if arg("--system-prompt").startswith("Tu es l'interviewer"):
    keys = [line.split("`")[1] for line in message.splitlines() if line.startswith("- `")]
    text = grade_text(keys, [2] * len(keys))
else:
    field = lambda name: re.search(rf"^- {name} : (\S+)", message, re.M).group(1)  # noqa: E731
    parts = re.search(r"exactement (\d+) questions", message)
    exercise = exercise_json(
        field("type"),
        field("style"),
        int(parts.group(1)) if parts else None,
        title=f"Exercice {field('slot')} du {message.splitlines()[0].split()[-1]}",
    )
    if "WebSearch" in arg("--tools"):
        emit(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "t1",
                            "name": "WebSearch",
                            "input": {"query": "chiffres"},
                        }
                    ]
                },
            }
        )
        emit(
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "t1",
                            "content": f'Links: [{{"title":"Source","url":"{SEARCH_URL}"}}]',
                        }
                    ],
                },
                "tool_use_result": {
                    "results": [{"content": [{"title": "Source", "url": SEARCH_URL}]}]
                },
            }
        )
    text = "Voici l'exercice.\n```json\n" + json.dumps(exercise, ensure_ascii=False) + "\n```"

for i in range(0, len(text), 11):
    emit(
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": text[i : i + 11]},
            },
        }
    )
emit(
    {
        "type": "assistant",
        "message": {"model": "claude-sonnet-5-5", "content": [{"type": "text", "text": text}]},
    }
)
emit(
    {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": text,
        "total_cost_usd": 0.02,
        "modelUsage": {"claude-sonnet-5-5": {}},
        "usage": {
            "input_tokens": 3,
            "cache_creation_input_tokens": 4200,
            "cache_read_input_tokens": 0,
            "output_tokens": 900,
        },
    }
)
