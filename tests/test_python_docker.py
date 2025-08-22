import docker
import pytest

from gpt_oss.tools.python_docker.docker_tool import call_python_script


try:
    _client = docker.from_env()
    _client.ping()
except Exception:
    pytest.skip("Docker is not available", allow_module_level=True)


def test_infinite_script_times_out_and_cleans_up():
    client = docker.from_env()
    before = {c.id for c in client.containers.list(all=True)}

    output = call_python_script("while True: pass")

    after = {c.id for c in client.containers.list(all=True)}

    assert "Execution timed out" in output
    assert before == after


def test_container_runs_as_nobody_and_is_read_only():
    script = (
        "import os, pwd\n"
        "print(pwd.getpwuid(os.getuid()).pw_name)\n"
        "try:\n"
        "    with open('/root_file', 'w') as f:\n"
        "        f.write('x')\n"
        "    print('writable')\n"
        "except Exception as e:\n"
        "    print(type(e).__name__)\n"
    )
    output = call_python_script(script)
    lines = [line.strip() for line in output.strip().splitlines() if line.strip()]
    assert lines[0] == 'nobody'
    assert lines[1] != 'writable'
