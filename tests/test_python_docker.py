import docker

from gpt_oss.tools.python_docker.docker_tool import call_python_script


def test_infinite_script_times_out_and_cleans_up():
    client = docker.from_env()
    before = {c.id for c in client.containers.list(all=True)}

    output = call_python_script("while True: pass")

    after = {c.id for c in client.containers.list(all=True)}

    assert "Execution timed out" in output
    assert before == after
