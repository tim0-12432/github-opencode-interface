
import os
from .workflows.implementation_workflow import ImplementationWorkflow


def main():
    env = dict(os.environ)
    workflow = env.get("WORKFLOW", "default")
    print(f"Starting workflow: {workflow}")
    if workflow == "implement":
        steps = ImplementationWorkflow(env.get("REPO"), int(env.get("ISSUE_NUMBER")), env.get("BRANCH"))
        steps.run(env)
    elif workflow == "suggest":
        steps = SuggestionWorkflow(env.get("REPO"))
        steps.run(env)
    elif workflow == "review":
        steps = ReviewWorkflow(env.get("REPO"))
        steps.run(env)
    else:
        print(f"Unknown workflow: {workflow}")

if __name__ == "__main__":
    main()
