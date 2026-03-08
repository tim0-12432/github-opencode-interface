from .step import AbstractStep
import subprocess

class GithubLoginStep(AbstractStep):
    def __init__(self):
        super().__init__(name="GitHub Login", retries=0)

    def run(self, env: dict):
        token = env.get("GITHUB_TOKEN")
        print("Setting up GitHub authentication...")
        try:
            subprocess.check_output([
                "gh",
                "auth", "login",
                "--with-token"
            ], text=True, input=token, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            print(f"GitHub authentication failed: {e.output}")
            raise
        try:
            subprocess.check_output([
                "gh",
                "auth", "status"
            ], text=True, stderr=subprocess.STDOUT)
            print("GitHub authenticated successfully")
        except subprocess.CalledProcessError as e:
            print(f"GitHub authentication verification failed: {e.output}")
            raise
        
        user_name = env.get("GITHUB_USER_NAME", "Issue Resolver Bot")
        try:
            subprocess.check_output([
                "git", "config", "--global", "user.name", user_name
            ], text=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            print(f"Failed to configure git user name: {e.output}")
            raise

        user_email = env.get("GITHUB_USER_EMAIL", "bot@issue-resolver.local")
        try:
            subprocess.check_output([
                "git", "config", "--global", "user.email", user_email
            ], text=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            print(f"Failed to configure git user email: {e.output}")
            raise
