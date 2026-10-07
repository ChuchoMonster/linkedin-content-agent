"""Buffer request building and the scheduling rules, with HTTP mocked out."""
import datetime
import io
import json
import sys
import urllib.error

import pytest

import buffer_draft
import buffer_schedule
from conftest import make_post

ET = buffer_schedule.ET
FAKE_ENV = {"BUFFER_ACCESS_TOKEN": "test-token", "BUFFER_LINKEDIN_CHANNEL_ID": "chan-123",
            "BUFFER_API_URL": "https://buffer.test/graphql"}


# --- .env loading and the GraphQL transport -----------------------------------

def test_load_env_parses_file_and_lets_real_environment_win(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text('# comment\n\nBUFFER_ACCESS_TOKEN="from-file"\n'
                        "ASSET_BASE_URL='https://cdn.example.com'\nnot a pair\nOTHER=1\n")
    monkeypatch.setenv("BUFFER_ACCESS_TOKEN", "from-shell")
    monkeypatch.setenv("BUFFER_EXTRA", "shell-only")
    monkeypatch.setenv("UNRELATED_SECRET", "must-not-leak")
    env = buffer_draft.load_env(env_file)
    assert env["BUFFER_ACCESS_TOKEN"] == "from-shell"
    assert env["ASSET_BASE_URL"] == "https://cdn.example.com"
    assert env["OTHER"] == "1"
    assert env["BUFFER_EXTRA"] == "shell-only"
    assert "UNRELATED_SECRET" not in env


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_graphql_posts_json_with_bearer_token(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["request"], seen["timeout"] = request, timeout
        return FakeResponse(b'{"data": {"ok": true}}')

    monkeypatch.setattr(buffer_draft.urllib.request, "urlopen", fake_urlopen)
    result = buffer_draft.graphql(FAKE_ENV, "query Q { x }", {"input": {"id": "p1"}})

    req = seen["request"]
    assert result == {"data": {"ok": True}}
    assert req.full_url == "https://buffer.test/graphql"
    assert req.get_method() == "POST"
    assert req.get_header("Authorization") == "Bearer test-token"
    assert req.get_header("Content-type") == "application/json"
    assert json.loads(req.data) == {"query": "query Q { x }", "variables": {"input": {"id": "p1"}}}
    assert seen["timeout"] == 30


def test_graphql_turns_http_error_into_errors_payload(monkeypatch):
    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {},
                                     io.BytesIO(b"bad token"))

    monkeypatch.setattr(buffer_draft.urllib.request, "urlopen", fake_urlopen)
    result = buffer_draft.graphql(FAKE_ENV, "q", {})
    assert result == {"errors": [{"message": "HTTP 401", "body": "bad token"}]}


# --- Eastern time -> UTC ---------------------------------------------------------

@pytest.mark.parametrize("stamp, expected", [
    ("2026-01-15T08:30", "2026-01-15T13:30:00+00:00"),   # EST, UTC-5
    ("2026-07-15T08:30", "2026-07-15T12:30:00+00:00"),   # EDT, UTC-4
    ("2026-07-15T08:30+00:00", "2026-07-15T08:30:00+00:00"),  # already aware
])
def test_to_utc_handles_daylight_saving(stamp, expected):
    assert buffer_schedule.to_utc(stamp).isoformat() == expected


# --- buffer_schedule.main --------------------------------------------------------

@pytest.fixture
def scheduler(monkeypatch, tmp_path):
    """Run buffer_schedule.main() with a fake env and a recording graphql."""
    calls = []
    responses = []

    def fake_graphql(env, query, variables):
        calls.append((query, variables))
        return responses.pop(0)

    monkeypatch.setattr(buffer_schedule, "load_env", lambda: dict(FAKE_ENV))
    monkeypatch.setattr(buffer_schedule, "graphql", fake_graphql)

    post = tmp_path / "post.md"
    post.write_text(make_post())

    def run(*argv):
        monkeypatch.setattr(sys, "argv", ["buffer_schedule.py", *argv])
        return buffer_schedule.main()

    run.calls, run.responses, run.post = calls, responses, post
    return run


def et_stamp(delta):
    return (datetime.datetime.now(ET) + delta).strftime("%Y-%m-%dT%H:%M")


def dry_run_input(capsys):
    out = capsys.readouterr().out
    return json.loads(out[out.index("{"):])["input"], out


def test_dry_run_builds_a_live_scheduled_post(scheduler, capsys):
    at = et_stamp(datetime.timedelta(days=2))
    scheduler(str(scheduler.post), "--at", at, "--dry-run")
    post_input, _ = dry_run_input(capsys)
    expected_due = buffer_schedule.to_utc(at).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    assert post_input == {
        "channelId": "chan-123",
        "text": make_post().strip(),
        "assets": [],
        "saveToDraft": False,
        "schedulingType": "automatic",
        "mode": "customScheduled",
        "dueAt": expected_due,
    }
    assert scheduler.calls == []


def test_refuses_to_schedule_a_post_that_fails_the_gates(scheduler, tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text(make_post(tags=None))
    with pytest.raises(SystemExit, match="Refusing to schedule"):
        scheduler(str(bad), "--at", et_stamp(datetime.timedelta(days=2)))
    assert scheduler.calls == []


def test_skip_validation_overrides_the_gates(scheduler, tmp_path, capsys):
    bad = tmp_path / "bad.md"
    bad.write_text(make_post(tags=None))
    scheduler(str(bad), "--at", et_stamp(datetime.timedelta(days=2)),
              "--skip-validation", "--dry-run")
    assert "Proceeding anyway" in capsys.readouterr().out


@pytest.mark.parametrize("delta, message", [
    (datetime.timedelta(minutes=5), "less than 15 minutes out"),
    (-datetime.timedelta(hours=2), "is in the past"),
])
def test_slot_without_a_cancel_window_is_refused(scheduler, delta, message):
    with pytest.raises(SystemExit, match=message):
        scheduler(str(scheduler.post), "--at", et_stamp(delta))
    assert scheduler.calls == []


def test_past_slot_with_now_if_past_publishes_immediately(scheduler, capsys):
    scheduler(str(scheduler.post), "--at", et_stamp(-datetime.timedelta(hours=2)),
              "--now-if-past", "--dry-run")
    post_input, out = dry_run_input(capsys)
    assert post_input["mode"] == "shareNow"
    assert "dueAt" not in post_input
    assert "would PUBLISH IMMEDIATELY" in out


def test_now_if_past_does_not_change_a_future_slot(scheduler, capsys):
    scheduler(str(scheduler.post), "--at", et_stamp(datetime.timedelta(days=1)),
              "--now-if-past", "--dry-run")
    post_input, _ = dry_run_input(capsys)
    assert post_input["mode"] == "customScheduled"


def test_document_attachment_is_built_from_hosted_urls(scheduler, capsys):
    scheduler(str(scheduler.post), "--at", et_stamp(datetime.timedelta(days=2)), "--dry-run",
              "--document", "https://cdn.example.com/x.pdf", "--document-title", "Six slides",
              "--thumbnail", "https://cdn.example.com/x-cover.png")
    post_input, _ = dry_run_input(capsys)
    assert post_input["assets"] == [{"document": {"url": "https://cdn.example.com/x.pdf",
                                                  "title": "Six slides",
                                                  "thumbnailUrl": "https://cdn.example.com/x-cover.png"}}]


@pytest.mark.parametrize("extra, message", [
    (["--document", "https://cdn.example.com/x.pdf"], "needs --document-title and --thumbnail"),
    (["--document", "build/x.pdf", "--document-title", "T", "--thumbnail",
      "https://cdn.example.com/c.png"], "must be a public https URL"),
])
def test_document_attachment_is_validated(scheduler, extra, message):
    with pytest.raises(SystemExit, match=message):
        scheduler(str(scheduler.post), "--at", et_stamp(datetime.timedelta(days=2)), *extra)


def test_live_schedule_reports_cancel_command(scheduler, capsys):
    scheduler.responses.append({"data": {"createPost": {"post": {"id": "p-9", "status": "scheduled"}}}})
    scheduler(str(scheduler.post), "--at", et_stamp(datetime.timedelta(days=2)))
    query, variables = scheduler.calls[0]
    assert query is buffer_draft.CREATE_POST
    assert variables["input"]["saveToDraft"] is False
    assert "buffer_schedule.py --cancel p-9" in capsys.readouterr().out


def test_live_schedule_fails_unless_buffer_reports_scheduled(scheduler):
    scheduler.responses.append({"data": {"createPost": {"post": {"id": "p-9", "status": "draft"}}}})
    with pytest.raises(SystemExit) as exc:
        scheduler(str(scheduler.post), "--at", et_stamp(datetime.timedelta(days=2)))
    assert exc.value.code == 1


def test_buffer_rejection_message_is_surfaced(scheduler):
    scheduler.responses.append({"data": {"createPost": {"message": "Channel disconnected"}}})
    with pytest.raises(SystemExit, match="Buffer rejected it: Channel disconnected"):
        scheduler(str(scheduler.post), "--at", et_stamp(datetime.timedelta(days=2)))


def test_cancel_sends_delete_mutation(scheduler, capsys):
    scheduler.responses.append({"data": {"deletePost": {"post": {"id": "p-9", "status": "deleted"}}}})
    scheduler("--cancel", "p-9")
    query, variables = scheduler.calls[0]
    assert "deletePost" in query
    assert variables == {"input": {"id": "p-9"}}
    assert "Cancelled p-9" in capsys.readouterr().out


# --- buffer_draft.main and buffer_status ---------------------------------------

@pytest.fixture
def drafter(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(buffer_draft, "load_env", lambda: dict(FAKE_ENV))
    post = tmp_path / "post.md"
    post.write_text("Draft text with 1 number.\n")

    def run(*argv, response=None):
        monkeypatch.setattr(buffer_draft, "graphql",
                            lambda env, q, v: calls.append(v) or response)
        monkeypatch.setattr(sys, "argv", ["buffer_draft.py", str(post), *argv])
        return buffer_draft.main()

    run.calls = calls
    return run


def test_draft_goes_to_queue_as_a_draft(drafter, capsys):
    drafter("--dry-run")
    out = capsys.readouterr().out
    assert json.loads(out)["input"] == {"channelId": "chan-123", "text": "Draft text with 1 number.",
                                        "assets": [], "saveToDraft": True,
                                        "schedulingType": "automatic", "mode": "addToQueue"}


def test_draft_with_due_date_is_still_a_draft(drafter, capsys):
    drafter("--due-at", "2026-12-01T13:30:00Z", "--image", "https://cdn.example.com/a.png",
            "--dry-run")
    post_input = json.loads(capsys.readouterr().out)["input"]
    assert post_input["saveToDraft"] is True
    assert post_input["mode"] == "customScheduled"
    assert post_input["dueAt"] == "2026-12-01T13:30:00Z"
    assert post_input["assets"] == [{"image": {"url": "https://cdn.example.com/a.png"}}]


def test_draft_that_comes_back_live_is_an_error(drafter):
    response = {"data": {"createPost": {"post": {"id": "d1", "status": "scheduled",
                                                 "channelId": "chan-123"}}}}
    with pytest.raises(SystemExit) as exc:
        drafter(response=response)
    assert exc.value.code == 1
