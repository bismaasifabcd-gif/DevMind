import docker
import os

client = docker.from_env()

def run_tests_in_docker(repo_path: str, test_command: str = "pytest") -> dict:
    """
    Runs tests inside an isolated Docker container using a Python base image.
    Mounts the repo_path into the container and executes the test command.
    """
    try:
        container = client.containers.run(
            image="python:3.11-slim",
            command=f"sh -c 'pip install pytest --quiet && {test_command}'",
            volumes={os.path.abspath(repo_path): {"bind": "/app", "mode": "rw"}},
            working_dir="/app",
            remove=False,
            detach=True,
        )
        result = container.wait(timeout=120)
        logs = container.logs().decode("utf-8", errors="ignore")
        exit_code = result.get("StatusCode", 1)
        container.remove()

        return {
            "passed": exit_code == 0,
            "stdout": logs,
            "stderr": ""
        }
    except Exception as e:
        return {"passed": False, "stdout": "", "stderr": str(e)}