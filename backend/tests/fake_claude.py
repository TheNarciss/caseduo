"""A fake `claude -p --output-format stream-json` for tests (copied into an executable).

Reads the user message on stdin and answers a valid grading for the rubric it
finds there, the way the real CLI streams it: init, text deltas, the whole
message, then the result. A `mode` file next to it set to `limit` or `auth`
answers the CLI's error instead. What it saw (arguments, names of environment
variables, stdin) goes to `cli.json` next to it: the backend passes it a minimal
environment on purpose, so nothing reaches it through variables.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(sys.argv[0]))


def emit(event):
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def grade_text(keys):
    scores = [
        {"key": k, "score": 2, "justification": "Une phrase.", "quote": "je vois trois axes"}
        for k in keys
    ]
    return (
        "<scores>\n" + json.dumps({"rubric_scores": scores, "score": 99}) + "\n</scores>\n"
        "<feedback>\n### Ce qui était bien\n- Plan clair.\n### À corriger\n- Chiffre → « je pose 30 % »\n"
        "### En 30 secondes tu aurais dû dire\n« Je recommande… »\n</feedback>\n"
        "<follow_up>\nEt si le budget était divisé par deux ?\n</follow_up>"
    )


message = sys.stdin.read()
with open(os.path.join(HERE, "cli.json"), "w") as log:
    json.dump({"argv": sys.argv[1:], "env": sorted(os.environ), "stdin": message}, log)
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

text = grade_text([line.split("`")[1] for line in message.splitlines() if line.startswith("- `")])
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
